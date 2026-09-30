from datetime import datetime, timezone

from app.core import storage
from app.core.storage_backend import get_backend
from app.models.annotation import Annotation, AnnotationIn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class AnnotationManager:
    """Bounding-box annotations, persisted to annotations.json per project."""

    def _load(self, project_id: str) -> list[Annotation]:
        if not storage.is_safe_id(project_id):
            return []
        raw = get_backend().read_doc(project_id, "annotations", [])

        annotations: list[Annotation] = []
        for item in raw:
            try:
                annotations.append(Annotation(**item))
            except Exception:
                # Skip legacy/invalid entries (e.g. old image-level labels
                # without bounding-box coordinates) instead of crashing.
                continue
        return annotations

    def _save(self, project_id: str, annotations: list[Annotation]) -> None:
        get_backend().write_doc(
            project_id,
            "annotations",
            [a.model_dump(mode="json") for a in annotations],
        )

    def _normalize_box(self, data: AnnotationIn) -> tuple[float, float, float, float]:
        x = _clamp(data.x, 0.0, 1.0)
        y = _clamp(data.y, 0.0, 1.0)
        width = _clamp(data.width, 0.0, 1.0 - x)
        height = _clamp(data.height, 0.0, 1.0 - y)

        if width <= 0 or height <= 0:
            raise ValueError("Bounding box must have positive width and height.")

        return x, y, width, height

    def list_all(self, project_id: str) -> list[Annotation]:
        return self._load(project_id)

    def list_for_image(self, project_id: str, image_id: str) -> list[Annotation]:
        return [a for a in self._load(project_id) if a.image_id == image_id]

    def get(self, project_id: str, annotation_id: str) -> Annotation | None:
        """Return one annotation by id, or ``None`` if it does not exist.

        Used by the routes to verify an annotation actually belongs to the
        image named in the request path before updating/deleting it, so a call
        against the wrong image URL can never mutate an unrelated annotation.
        """
        for annotation in self._load(project_id):
            if annotation.id == annotation_id:
                return annotation
        return None

    def count(self, project_id: str) -> int:
        return len(self._load(project_id))

    def count_for_label(self, project_id: str, label_id: str) -> int:
        """How many annotations reference ``label_id``.

        Used to block deletion of a label that is still in use (M1 label
        deletion integrity), so annotations are never silently orphaned.
        """
        if not label_id:
            return 0
        return sum(1 for a in self._load(project_id) if a.label_id == label_id)

    def create(
        self,
        project_id: str,
        image_id: str,
        data: AnnotationIn,
    ) -> Annotation:
        x, y, width, height = self._normalize_box(data)

        annotation = Annotation(
            image_id=image_id,
            label_id=data.label_id,
            label=data.label,
            x=x,
            y=y,
            width=width,
            height=height,
        )

        annotations = self._load(project_id)
        annotations.append(annotation)
        self._save(project_id, annotations)

        return annotation

    def update(
        self,
        project_id: str,
        annotation_id: str,
        data: AnnotationIn,
    ) -> Annotation | None:
        x, y, width, height = self._normalize_box(data)

        annotations = self._load(project_id)

        for annotation in annotations:
            if annotation.id == annotation_id:
                annotation.label_id = data.label_id
                annotation.label = data.label
                annotation.x = x
                annotation.y = y
                annotation.width = width
                annotation.height = height
                annotation.updated_at = _now()

                self._save(project_id, annotations)
                return annotation

        return None

    def delete(self, project_id: str, annotation_id: str) -> bool:
        annotations = self._load(project_id)
        remaining = [a for a in annotations if a.id != annotation_id]

        if len(remaining) == len(annotations):
            return False

        self._save(project_id, remaining)
        return True

    def delete_for_image(self, project_id: str, image_id: str) -> int:
        annotations = self._load(project_id)
        remaining = [a for a in annotations if a.image_id != image_id]

        removed = len(annotations) - len(remaining)
        if removed:
            self._save(project_id, remaining)

        return removed


manager = AnnotationManager()
