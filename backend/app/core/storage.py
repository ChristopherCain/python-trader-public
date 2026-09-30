import json
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings


def is_safe_id(value: str) -> bool:
    """True if ``value`` is safe to use as a single filesystem path component.

    Every application id is a ``uuid4`` string, so this accepts all legitimate
    ids while rejecting anything that could escape the storage root: empty
    values, path separators, parent references (``..``) and null bytes. Used to
    stop a crafted ``project_id`` from redirecting reads/writes/deletes outside
    ``UPLOAD_DIR`` (path traversal).
    """
    return bool(value) and not (
        "/" in value
        or "\\" in value
        or ".." in value
        or "\x00" in value
    )


def project_dir(project_id: str) -> Path:
    # Defense in depth: never build a filesystem path from an unsafe id.
    # Callers guard first and return the API's not-found convention, so this
    # raise is a safety net that should be unreachable in normal operation.
    if not is_safe_id(project_id):
        raise ValueError(f"Unsafe project id: {project_id!r}")
    return settings.UPLOAD_DIR / project_id


def images_dir(project_id: str) -> Path:
    return project_dir(project_id) / "images"


def thumbnails_dir(project_id: str) -> Path:
    return project_dir(project_id) / "thumbnails"


def export_dir(project_id: str) -> Path:
    return project_dir(project_id) / "export"


def annotations_dir(project_id: str) -> Path:
    return project_dir(project_id) / "annotations"


def metadata_path(project_id: str) -> Path:
    return project_dir(project_id) / "metadata.json"


def images_index_path(project_id: str) -> Path:
    return project_dir(project_id) / "images.json"


def labels_path(project_id: str) -> Path:
    return project_dir(project_id) / "labels.json"


def annotations_path(project_id: str) -> Path:
    return annotations_dir(project_id) / "annotations.json"


def read_json(path: Path, default: Any) -> Any:
    """Read JSON, returning ``default`` when the file is missing or corrupt."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    """Atomically write JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file then replace, so a crash mid-write cannot
    # leave a half-written index behind.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
