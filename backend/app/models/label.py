from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# A small default palette so labels get distinct colors in the UI.
DEFAULT_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e",
    "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899",
]


class Label(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    name: str
    color: str = "#3b82f6"
    created_at: datetime = Field(default_factory=_now)
