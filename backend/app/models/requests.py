from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    # Only the name is client-supplied. Timestamps (created_at, expires_at) are
    # generated server-side, and unknown keys are ignored, so a request cannot
    # set or extend a project's lifetime by sending its own values.
    model_config = ConfigDict(extra="ignore")

    name: str | None = None


class ProjectUpdate(BaseModel):
    # Same rule as above: no timestamp field is writable through the API.
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    status: str | None = None


class LabelCreate(BaseModel):
    name: str
    color: str | None = None


class LabelUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
