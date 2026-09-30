from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core import storage
from app.core.config import settings
from app.core.storage_backend import get_backend
from app.models.image import Image
from app.services.project.manager import manager as project_manager

try:
    from PIL import Image as PILImage  # optional: used to read dimensions
except Exception:  # pragma: no cover - pillow may not be installed
    PILImage = None


class UploadError(Exception):
    """Raised when an uploaded file is rejected."""


def _looks_like_allowed_image(data: bytes) -> bool:
    """Content sniff for the allowed image types via their magic bytes.

    A defence-in-depth check on top of the extension allow-list: it stops a
    non-image payload wearing an image extension from being stored. Only applied
    for the public (cloud) deployment so self-hosted v1.0.0 behavior is
    unchanged.
    """
    if data[:3] == b"\xff\xd8\xff":  # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WebP (RIFF container)
        return True
    return False


class UploadManager:
    """Image storage where the filesystem index (images.json) is the source
    of truth, so uploads survive a backend restart."""

    def _load(self, project_id: str) -> list[Image]:
        if not storage.is_safe_id(project_id):
            return []
        raw = get_backend().read_doc(project_id, "images", [])
        images: list[Image] = []
        for item in raw:
            try:
                images.append(Image(**item))
            except Exception:
                continue
        return images

    def _save(self, project_id: str, images: list[Image]) -> None:
        get_backend().write_doc(
            project_id,
            "images",
            [img.model_dump(mode="json") for img in images],
        )

    def _unique_filename(self, project_id: str, original: str) -> str:
        """Avoid collisions when two uploads share a name."""
        stem = Path(original).stem
        suffix = Path(original).suffix.lower()
        candidate = f"{stem}{suffix}"
        existing = {img.filename for img in self._load(project_id)}
        if candidate not in existing and not get_backend().image_exists(
            project_id, candidate
        ):
            return candidate
        return f"{stem}_{uuid4().hex[:8]}{suffix}"

    def upload_image(self, project_id: str, file: UploadFile) -> Image | None:
        if not project_manager.exists(project_id):
            return None

        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise UploadError(
                f"Unsupported file type '{suffix or 'unknown'}'. "
                f"Allowed: {', '.join(sorted(settings.ALLOWED_IMAGE_EXTENSIONS))}."
            )

        existing_images = self._load(project_id)

        # Abuse protection applies ONLY to the public (cloud) deployment, so the
        # local/self-hosted workflow keeps v1.0.0 behavior exactly: no size cap,
        # no per-project quota, no content sniffing.
        if settings.is_cloud:
            if len(existing_images) >= settings.MAX_IMAGES_PER_PROJECT:
                raise UploadError(
                    f"Project image limit reached "
                    f"({settings.MAX_IMAGES_PER_PROJECT} images)."
                )

            # Bounded read so a huge body cannot exhaust memory or fill the
            # bucket; read one byte past the cap to detect an over-limit file.
            data = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
            if len(data) > settings.MAX_UPLOAD_BYTES:
                raise UploadError(
                    f"Image too large: exceeds the "
                    f"{settings.MAX_UPLOAD_BYTES} byte limit."
                )

            # The extension must not be the only thing standing between a
            # non-image payload and storage.
            if not _looks_like_allowed_image(data):
                raise UploadError(
                    f"File '{file.filename}' is not a valid JPG/PNG/WebP image."
                )

            # Per-project total-size quota.
            used = sum(img.size for img in existing_images)
            if used + len(data) > settings.MAX_PROJECT_BYTES:
                raise UploadError(
                    "Project storage limit reached "
                    f"({settings.MAX_PROJECT_BYTES} bytes)."
                )
        else:
            data = file.file.read()

        stored_name = self._unique_filename(project_id, file.filename or "image")

        width = height = None
        if PILImage is not None:
            try:
                with PILImage.open(BytesIO(data)) as im:
                    width, height = im.size
            except Exception:
                pass  # dimensions are best-effort

        stored_ref = get_backend().write_image(project_id, stored_name, data)

        image = Image(
            filename=stored_name,
            original_filename=file.filename or stored_name,
            filepath=stored_ref,
            size=len(data),
            width=width,
            height=height,
        )

        images = existing_images
        images.append(image)
        self._save(project_id, images)

        # Project image/annotation counts are recomputed lazily from disk on the
        # next read (get_project / list_projects / touch_opened). We deliberately
        # do NOT refresh here: doing so re-read every image + annotation file per
        # uploaded file, making a bulk upload O(n^2). The stored count is only a
        # cache, so leaving it stale until the next read changes no served value.
        return image

    def list_images(self, project_id: str) -> list[Image]:
        return self._load(project_id)

    def get_image(self, project_id: str, image_id: str) -> Image | None:
        for image in self._load(project_id):
            if image.id == image_id:
                return image
        return None

    def delete_image(self, project_id: str, image_id: str) -> bool:
        images = self._load(project_id)
        target = next((img for img in images if img.id == image_id), None)
        if target is None:
            return False

        # Blob first, index second — deliberately. The index is what makes an
        # image reachable, so if the blob delete fails (it raises for real cloud
        # errors) the entry survives and the user can retry; dropping the index
        # first would strand an unreachable object in the bucket forever.
        get_backend().delete_image(project_id, target.filename)

        self._save(project_id, [img for img in images if img.id != image_id])

        # Remove annotations tied to this image, then refresh counts.
        from app.services.annotation.manager import manager as annotation_manager

        annotation_manager.delete_for_image(project_id, image_id)
        project_manager.get_project(project_id)

        return True


manager = UploadManager()
