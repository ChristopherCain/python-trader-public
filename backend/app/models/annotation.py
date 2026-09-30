from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Annotation(BaseModel):
    """A bounding box on an image.

    Coordinates are normalized to the range 0..1 relative to the image
    dimensions, where (x, y) is the top-left corner. Storing normalized
    values keeps annotations correct no matter what size the image is
    displayed at in the browser.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    image_id: str

    label_id: str | None = None
    label: str = ""

    x: float
    y: float
    width: float
    height: float

    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class AnnotationIn(BaseModel):
    """Payload for creating or updating an annotation."""

    label_id: str | None = None
    label: str = ""

    x: float
    y: float
    width: float
    height: float
