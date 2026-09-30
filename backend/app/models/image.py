from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Image(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str          # stored filename on disk (unique within project)
    original_filename: str = ""  # name as uploaded by the user
    filepath: str
    size: int = 0

    width: int | None = None
    height: int | None = None

    created_at: datetime = Field(default_factory=_now)
