"""Shared pytest fixtures for the backend regression suite.

Goals of this suite (M0 — regression safety net):
  * Lock in the *current, verified* MVP behavior so future refactors that
    change it will fail loudly. These tests assert what the code does today,
    not a wished-for spec.
  * Touch NO real user data. Every test runs against a throwaway temp
    directory, so running the suite never reads or writes the real
    ``backend/uploads`` / ``exports`` / ``checkpoints`` folders.

Isolation mechanism
-------------------
``app.core.storage`` derives every path from ``settings.UPLOAD_DIR`` *at call
time* (e.g. ``settings.UPLOAD_DIR / project_id``), never caching it at import.
So pointing ``settings.UPLOAD_DIR`` at a per-test ``tmp_path`` fully isolates
storage without any production-code change. We repoint the other storage roots
too, purely so the startup hook can't create real folders during a test run.

Import note
-----------
The backend has no ``__init__.py`` files (it relies on namespace packages and
is always launched from ``backend/``). To let ``import app...`` resolve during
test collection, this conftest inserts the ``backend/`` directory onto
``sys.path`` before any test module imports the app.
"""

import base64
import sys
from pathlib import Path

import pytest

# --- Make `import app...` work exactly like `uvicorn app.main:app` from backend/ ---
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# A real, minimal 1x1 PNG. Using genuine image bytes means the upload path,
# and Pillow's optional dimension read, behave just like a real upload — while
# keeping the tests free of any binary fixture files on disk.
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png_bytes() -> bytes:
    """Raw bytes of a valid 1x1 PNG for upload tests."""
    return _PNG_1x1


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Point every storage root at a fresh temp dir for each test.

    ``autouse=True`` so no test can accidentally hit real data. We patch the
    attributes on the shared ``settings`` singleton; because every module holds
    the same object by reference, the change is visible everywhere at once.
    """
    from app.core import storage_backend
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(settings, "EXPORT_DIR", tmp_path / "exports")
    monkeypatch.setattr(settings, "PROJECT_DIR", tmp_path / "projects")
    monkeypatch.setattr(settings, "CHECKPOINT_DIR", tmp_path / "checkpoints")

    # Pin the baseline to local mode. ``Settings`` reads backend/.env, so a
    # developer who has STORAGE_BACKEND=cloud there would otherwise run this
    # whole suite against real Supabase. Cloud tests opt in explicitly via the
    # ``cloud`` fixture, which installs an in-memory backend first.
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    # Drop the cached backend so it is rebuilt for the pinned mode (monkeypatch
    # restores the previous value, keeping tests independent of each other).
    monkeypatch.setattr(storage_backend, "_backend", None)

    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def client(isolated_storage):
    """A FastAPI TestClient bound to the isolated storage dirs.

    Created *after* ``isolated_storage`` has repointed ``settings`` so the
    startup hook (``ensure_storage_dirs``) builds folders under ``tmp_path``,
    not the real backend directory.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


# ---- small request helpers (kept here so every test module can reuse them) ----

def make_project(client, name="Test Project"):
    """Create a project via the API and return its JSON ``data`` dict."""
    resp = client.post("/projects", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def upload_png(client, project_id, filename, png_bytes):
    """Upload a single PNG and return the created image ``data`` dict."""
    resp = client.post(
        f"/projects/{project_id}/images",
        files=[("files", (filename, png_bytes, "image/png"))],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["uploaded"], resp.text
    return body["uploaded"][0]


def make_label(client, project_id, name, color=None):
    """Create a label and return its JSON ``data`` dict."""
    payload = {"name": name}
    if color is not None:
        payload["color"] = color
    resp = client.post(f"/projects/{project_id}/labels", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def make_annotation(client, project_id, image_id, box, label=None):
    """Create an annotation and return its JSON ``data`` dict.

    ``box`` is a dict with x/y/width/height; ``label`` is an optional label
    ``data`` dict whose id/name are attached to the annotation.
    """
    payload = dict(box)
    if label is not None:
        payload["label_id"] = label["id"]
        payload["label"] = label["name"]
    resp = client.post(
        f"/projects/{project_id}/images/{image_id}/annotations",
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]
