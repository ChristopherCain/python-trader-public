"""Deployment / storage-abstraction regression tests.

These cover the public-web-deployment adaptation without changing any v1.0.0
behavior. The suite has two halves:

1. **Cloud path via a fake backend.** ``FakeCloudBackend`` implements the
   ``StorageBackend`` interface in memory, so the *entire* FastAPI stack runs in
   ``STORAGE_BACKEND=cloud`` mode with no network and no local persistent disk.
   This proves the managers/routes are backend-agnostic and that the logical
   data model (Project/Image/Label/Annotation), the M2 integrity rules, YOLO
   export, upload validation, abuse limits, temp cleanup, and TTL cleanup all
   work against a non-local store.

2. **Real Supabase adapter, offline.** A few focused tests exercise
   ``SupabaseStorageBackend``'s object-key layout and credential guard by
   stubbing its byte-level REST helpers — verifying the mapping that would
   otherwise only be exercised against a live Supabase project.

Nothing here touches real user data (the autouse ``isolated_storage`` fixture
repoints every storage root at a temp dir) and nothing weakens the existing
53-test suite: those never set ``STORAGE_BACKEND``, so they keep running the
local path unchanged.
"""

from datetime import datetime, timedelta, timezone

import pytest

from conftest import (  # noqa: E402  (path set up by conftest)
    make_annotation,
    make_label,
    make_project,
    upload_png,
)


# ---------------------------------------------------------------------------
# In-memory cloud backend + fixture
# ---------------------------------------------------------------------------

class FakeCloudBackend:
    """A StorageBackend that keeps everything in memory.

    Mirrors the *semantics* of ``SupabaseStorageBackend`` (object keys, JSON
    docs, streamed image responses) without any I/O, so tests can drive the
    cloud code path deterministically.
    """

    def __init__(self):
        # (project_id, doc) -> python object; (project_id, stored_name) -> bytes
        self.docs: dict[tuple[str, str], object] = {}
        self.images: dict[tuple[str, str], bytes] = {}

    # project lifecycle
    def init_project(self, project_id):
        return None  # object storage has no dirs to create

    def list_project_ids(self):
        ids = {pid for (pid, _doc) in self.docs}
        ids |= {pid for (pid, _name) in self.images}
        return sorted(ids)

    def delete_project(self, project_id):
        before = len(self.docs) + len(self.images)
        self.docs = {k: v for k, v in self.docs.items() if k[0] != project_id}
        self.images = {k: v for k, v in self.images.items() if k[0] != project_id}
        return (len(self.docs) + len(self.images)) < before

    # JSON documents
    def read_doc(self, project_id, doc, default):
        return self.docs.get((project_id, doc), default)

    def write_doc(self, project_id, doc, data):
        self.docs[(project_id, doc)] = data

    # image blobs
    def image_exists(self, project_id, stored_name):
        return (project_id, stored_name) in self.images

    def write_image(self, project_id, stored_name, data):
        self.images[(project_id, stored_name)] = data
        return f"{project_id}/images/{stored_name}"  # a "key", not a local path

    def read_image_bytes(self, project_id, stored_name):
        return self.images.get((project_id, stored_name))

    def delete_image(self, project_id, stored_name):
        self.images.pop((project_id, stored_name), None)

    def image_response(self, project_id, image):
        from fastapi.responses import StreamingResponse

        data = self.read_image_bytes(project_id, image.filename) or b""
        return StreamingResponse(iter([data]), media_type="image/png")


@pytest.fixture
def cloud(tmp_path, monkeypatch):
    """Run the app in cloud mode against a fresh ``FakeCloudBackend``.

    Yields ``(TestClient, FakeCloudBackend)``. The fake backend is installed
    *before* STORAGE_BACKEND is flipped to "cloud", so nothing ever tries to
    build a real ``SupabaseStorageBackend``.
    """
    from fastapi.testclient import TestClient

    from app.core import storage_backend
    from app.core.config import settings

    fake = FakeCloudBackend()
    # Install the fake first so get_backend() never constructs the real one.
    monkeypatch.setattr(storage_backend, "_backend", fake)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloud")
    # Export still uses local disk as *scratch*; keep it under tmp_path.
    monkeypatch.setattr(settings, "EXPORT_DIR", tmp_path / "exports")

    from app.main import app

    with TestClient(app) as client:
        yield client, fake


# ---------------------------------------------------------------------------
# Health / env / CORS
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


def test_env_config_defaults():
    """Defaults keep the app local-first and the limits sane."""
    from app.core.config import settings

    assert settings.STORAGE_BACKEND == "local"
    assert settings.is_cloud is False
    assert settings.MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    assert settings.MAX_IMAGES_PER_PROJECT == 100
    assert settings.MAX_PROJECT_BYTES == 200 * 1024 * 1024
    assert settings.PROJECT_TTL_HOURS == 30
    # TTL is cloud-only: a self-hosted instance never expires anything.
    assert settings.project_ttl_enabled is False
    # Secrets are never hard-coded.
    assert settings.SUPABASE_SERVICE_KEY == ""
    assert settings.MAINTENANCE_TOKEN == ""


def test_all_cors_origins_appends_frontend_origin(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "FRONTEND_ORIGIN", "https://demo.pages.dev")
    origins = settings.all_cors_origins
    assert "https://demo.pages.dev" in origins
    # Local dev origins are preserved so self-hosting/dev still works.
    assert "http://localhost:5173" in origins
    # No duplicates if it were already present.
    monkeypatch.setattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173")
    assert settings.all_cors_origins.count("http://localhost:5173") == 1


def test_cors_preflight_allows_local_origin(client):
    resp = client.options(
        "/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Local path still works after the refactor (spot check; full coverage lives in
# the existing suite, which runs entirely on the local backend).
# ---------------------------------------------------------------------------

def test_local_end_to_end_after_refactor(client, png_bytes):
    project = make_project(client, "Local E2E")
    image = upload_png(client, project["id"], "pic.png", png_bytes)
    label = make_label(client, project["id"], "cat")
    make_annotation(
        client,
        project["id"],
        image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3},
        label,
    )
    # Export produces a real zip.
    resp = client.get(f"/projects/{project['id']}/export/yolo")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert resp.content[:2] == b"PK"


# ---------------------------------------------------------------------------
# Cloud path: full workflow + persistence + serving
# ---------------------------------------------------------------------------

def test_cloud_full_workflow(cloud, png_bytes):
    client, fake = cloud

    project = make_project(client, "Cloud Project")
    pid = project["id"]

    # Metadata + the three index docs were written to the (cloud) backend, not
    # to local disk.
    assert (pid, "metadata") in fake.docs
    assert (pid, "images") in fake.docs
    assert (pid, "labels") in fake.docs
    assert (pid, "annotations") in fake.docs

    image = upload_png(client, pid, "pic.png", png_bytes)
    # The image blob is in object storage; its bytes round-trip.
    assert fake.read_image_bytes(pid, image["filename"]) == png_bytes

    label = make_label(client, pid, "cat")
    make_annotation(
        client, pid, image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )

    # Reads come straight back through the API.
    anns = client.get(f"/projects/{pid}/images/{image['id']}/annotations").json()
    assert len(anns["data"]) == 1
    assert anns["data"][0]["label"] == "cat"

    # Counts refresh from the backend, not disk.
    got = client.get(f"/projects/{pid}").json()["data"]
    assert got["images"] == 1
    assert got["annotations"] == 1


def test_cloud_persistence_is_backend_not_disk(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Persist")
    upload_png(client, project["id"], "pic.png", png_bytes)

    # A brand-new client sharing the same backend still sees the project — proof
    # that the source of truth is the (cloud) store, so an ephemeral-disk restart
    # loses nothing.
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client2:
        listed = client2.get("/projects").json()["data"]
        assert any(p["id"] == project["id"] for p in listed)
        imgs = client2.get(f"/projects/{project['id']}/images").json()["data"]
        assert len(imgs) == 1


def test_cloud_image_serving(cloud, png_bytes):
    client, _fake = cloud
    project = make_project(client, "Serve")
    image = upload_png(client, project["id"], "pic.png", png_bytes)

    resp = client.get(f"/projects/{project['id']}/images/{image['id']}/file")
    assert resp.status_code == 200
    assert resp.content == png_bytes


def test_cloud_delete_image_removes_blob(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Del")
    pid = project["id"]
    image = upload_png(client, pid, "pic.png", png_bytes)
    assert fake.image_exists(pid, image["filename"])

    resp = client.delete(f"/projects/{pid}/images/{image['id']}")
    assert resp.status_code == 200
    assert not fake.image_exists(pid, image["filename"])


# ---------------------------------------------------------------------------
# Cloud path: upload validation + abuse limits (cloud-only by design)
# ---------------------------------------------------------------------------

def test_cloud_rejects_oversize_upload(cloud, png_bytes, monkeypatch):
    client, _fake = cloud
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 10)  # bytes
    project = make_project(client, "Big")
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("pic.png", png_bytes, "image/png"))],
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["skipped"]


def test_cloud_rejects_non_image_content(cloud, monkeypatch):
    client, _fake = cloud
    project = make_project(client, "Fake")
    # A .png extension but non-image bytes: the content sniff must catch it.
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("evil.png", b"not really an image", "image/png"))],
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["skipped"]


def test_cloud_enforces_image_count_limit(cloud, png_bytes, monkeypatch):
    client, _fake = cloud
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_IMAGES_PER_PROJECT", 1)
    project = make_project(client, "Count")
    upload_png(client, project["id"], "a.png", png_bytes)  # first ok
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("b.png", png_bytes, "image/png"))],
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["skipped"]


def test_cloud_enforces_project_byte_limit(cloud, png_bytes, monkeypatch):
    client, _fake = cloud
    from app.core.config import settings

    project = make_project(client, "Bytes")
    first = upload_png(client, project["id"], "a.png", png_bytes)
    # Cap total bytes at exactly what one image used, so a second exceeds it.
    monkeypatch.setattr(settings, "MAX_PROJECT_BYTES", first["size"])
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("b.png", png_bytes, "image/png"))],
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["skipped"]


def test_cloud_rejects_unsupported_extension(cloud):
    client, _fake = cloud
    project = make_project(client, "Ext")
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["skipped"]


# ---------------------------------------------------------------------------
# Cloud path: YOLO export (format, stem collision, temp cleanup)
# ---------------------------------------------------------------------------

def _read_zip(content):
    import io
    import zipfile

    return zipfile.ZipFile(io.BytesIO(content))


def test_cloud_yolo_export_format_and_stem_collision(cloud, png_bytes):
    client, _fake = cloud
    project = make_project(client, "Export")
    pid = project["id"]

    # Two images that collide on stem (cat.jpg + cat.png) — both use valid image
    # bytes (the sniff checks content, not the extension), so both upload.
    img_jpg = upload_png(client, pid, "cat.jpg", png_bytes)
    img_png = upload_png(client, pid, "cat.png", png_bytes)

    label = make_label(client, pid, "cat")  # class index 0
    make_annotation(
        client, pid, img_jpg["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )
    make_annotation(
        client, pid, img_png["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )

    resp = client.get(f"/projects/{pid}/export/yolo")
    assert resp.status_code == 200
    zf = _read_zip(resp.content)
    names = set(zf.namelist())

    # Stem collision disambiguated: both label files survive (M2 rule).
    assert "dataset/labels/cat.txt" in names
    assert "dataset/labels/cat_1.txt" in names
    assert "dataset/classes.txt" in names

    # YOLO center format, class 0, normalized to 6 dp: cx=0.3, cy=0.35.
    line = zf.read("dataset/labels/cat.txt").decode().strip()
    assert line == "0 0.300000 0.350000 0.400000 0.300000"


def test_cloud_export_orphan_report(cloud, png_bytes):
    client, _fake = cloud
    project = make_project(client, "Orphan")
    pid = project["id"]
    image = upload_png(client, pid, "pic.png", png_bytes)
    # Annotation with no label -> orphan; must be reported, not silently dropped.
    make_annotation(
        client, pid, image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, None,
    )
    resp = client.get(f"/projects/{pid}/export/yolo")
    zf = _read_zip(resp.content)
    assert "dataset/unlabeled.txt" in zf.namelist()
    report = zf.read("dataset/unlabeled.txt").decode()
    assert "total_skipped\t1" in report


def test_cloud_export_cleans_up_scratch(cloud, png_bytes):
    client, _fake = cloud
    from app.core.config import settings
    from app.core import storage

    project = make_project(client, "Cleanup")
    pid = project["id"]
    upload_png(client, pid, "pic.png", png_bytes)

    resp = client.get(f"/projects/{pid}/export/yolo")
    assert resp.status_code == 200
    # In cloud mode the background task removes the scratch build + zip so the
    # ephemeral disk is not left holding generated archives.
    export_root = storage.export_dir(pid)
    assert not (export_root / "dataset").exists()
    assert not (export_root / "dataset_yolo.zip").exists()


# ---------------------------------------------------------------------------
# Cloud path: temp-project TTL cleanup + maintenance endpoint guards
# ---------------------------------------------------------------------------

def test_maintenance_cleanup_deletes_expired(cloud, monkeypatch):
    client, fake = cloud
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAINTENANCE_TOKEN", "secret-token")
    monkeypatch.setattr(settings, "PROJECT_TTL_HOURS", 30)

    fresh = make_project(client, "Fresh")
    old = make_project(client, "Old")

    # Simulate an aged project by rewinding both stored timestamps. ``expires_at``
    # is what the sweep actually judges (see test_ttl.py), and it is stamped
    # server-side at creation, so this is the only way to age a project at all.
    meta = fake.docs[(old["id"], "metadata")]
    aged = datetime.now(timezone.utc) - timedelta(hours=48)
    meta["created_at"] = aged.isoformat()
    meta["expires_at"] = (aged + timedelta(hours=30)).isoformat()

    resp = client.post(
        "/maintenance/cleanup", headers={"X-Maintenance-Token": "secret-token"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["enabled"] is True
    assert data["deleted"] == 1

    remaining = {p["id"] for p in client.get("/projects").json()["data"]}
    assert old["id"] not in remaining
    assert fresh["id"] in remaining


def test_maintenance_cleanup_rejects_bad_token(cloud, monkeypatch):
    client, _fake = cloud
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAINTENANCE_TOKEN", "secret-token")
    resp = client.post(
        "/maintenance/cleanup", headers={"X-Maintenance-Token": "wrong"}
    )
    assert resp.status_code == 401


def test_maintenance_cleanup_disabled_without_token(cloud):
    client, _fake = cloud
    # No MAINTENANCE_TOKEN configured -> endpoint is a hard 404 (never open).
    resp = client.post("/maintenance/cleanup")
    assert resp.status_code == 404


def test_maintenance_cleanup_disabled_in_local_mode(client):
    # Local (self-hosted) mode never exposes cleanup, even if a token existed.
    resp = client.post(
        "/maintenance/cleanup", headers={"X-Maintenance-Token": "anything"}
    )
    assert resp.status_code == 404


def test_cleanup_is_noop_in_local_mode(monkeypatch):
    """The manager method itself refuses to act outside cloud mode."""
    from app.core.config import settings
    from app.services.project.manager import manager as project_manager

    # Local mode: even with a TTL set, nothing is deleted.
    assert settings.is_cloud is False
    result = project_manager.cleanup_expired_projects()
    assert result == {"enabled": False, "deleted": 0, "checked": 0, "failed": 0}


# ---------------------------------------------------------------------------
# Real Supabase adapter (offline): key layout + credential guard
# ---------------------------------------------------------------------------

def test_supabase_requires_credentials(monkeypatch):
    from app.core.config import settings
    from app.core.storage_backend import SupabaseStorageBackend

    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")
    with pytest.raises(RuntimeError):
        SupabaseStorageBackend()


def test_supabase_object_url_and_key_layout(monkeypatch):
    from app.core.config import settings
    from app.core.storage_backend import SupabaseStorageBackend

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://ref.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "svc-key")
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "bucket")

    backend = SupabaseStorageBackend()

    # Object URL mirrors the documented REST path.
    assert backend._object_url("pid/metadata.json") == (
        "https://ref.supabase.co/storage/v1/object/bucket/pid/metadata.json"
    )

    # Stub the byte-level helpers so read/write map to the right keys with no I/O.
    store: dict[str, bytes] = {}
    monkeypatch.setattr(backend, "_put_bytes", lambda key, data, ct: store.__setitem__(key, data))
    monkeypatch.setattr(backend, "_get_bytes", lambda key: store.get(key))

    backend.write_doc("pid", "metadata", {"a": 1})
    assert "pid/metadata.json" in store
    assert backend.read_doc("pid", "metadata", None) == {"a": 1}

    key = backend.write_image("pid", "pic.png", b"\x89PNG...")
    assert key == "pid/images/pic.png"
    assert backend.read_image_bytes("pid", "pic.png") == b"\x89PNG..."
    assert backend.image_exists("pid", "pic.png") is True

    # Missing doc returns the provided default.
    assert backend.read_doc("pid", "labels", []) == []


# ---------------------------------------------------------------------------
# Supabase "object does not exist" handling (regression: upload 500)
#
# Supabase Storage answers a GET for an absent key with 400 + a JSON body whose
# statusCode is "404". _get_bytes used to treat that as a hard error, so the
# existence probe in _unique_filename raised HTTPStatusError and the very first
# upload of any image returned 500. Missing must read as absent; every other
# failure must still surface.
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for httpx.Response covering what _get_bytes touches."""

    def __init__(self, status_code, json_body=None, content=b"", text=""):
        self.status_code = status_code
        self._json = json_body
        self.content = content
        self.text = text or (content.decode("utf-8", "replace") if content else "")

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json

    def raise_for_status(self):
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Client error '{self.status_code}'",
                request=httpx.Request("GET", "https://ref.supabase.co/x"),
                response=httpx.Response(self.status_code),
            )

    # _delete_keys goes through client.request(...) rather than client.get.
    def request(self, *args, **kwargs):
        return self


def _supabase(monkeypatch, response):
    """A SupabaseStorageBackend whose HTTP calls return ``response``, no I/O."""
    from app.core.config import settings
    from app.core.storage_backend import SupabaseStorageBackend

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://ref.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "svc-key")
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "projects")

    backend = SupabaseStorageBackend()

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url):
            return response

        # _delete_keys uses client.request("DELETE", ...).
        def request(self, *args, **kwargs):
            return response

    monkeypatch.setattr(backend, "_client", lambda: _Client())
    return backend


def test_missing_object_400_envelope_reads_as_absent(monkeypatch):
    """The exact response Supabase returned in the reported traceback."""
    backend = _supabase(
        monkeypatch,
        _FakeResponse(
            400,
            {"statusCode": "404", "error": "not_found", "message": "Object not found"},
        ),
    )

    assert backend.image_exists("pid", "car.jpg") is False
    assert backend.read_image_bytes("pid", "car.jpg") is None
    # Documents not written yet must still fall back to their default.
    assert backend.read_doc("pid", "labels", []) == []


def test_missing_object_plain_404_still_reads_as_absent(monkeypatch):
    backend = _supabase(monkeypatch, _FakeResponse(404, {"message": "Not found"}))
    assert backend.image_exists("pid", "car.jpg") is False


def test_existing_object_is_still_detected(monkeypatch):
    backend = _supabase(monkeypatch, _FakeResponse(200, None, b"\x89PNG\r\n\x1a\n"))
    assert backend.image_exists("pid", "car.jpg") is True
    assert backend.read_image_bytes("pid", "car.jpg") == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize(
    "response",
    [
        # Bad/expired service key.
        _FakeResponse(401, {"statusCode": "401", "message": "Invalid JWT"}),
        _FakeResponse(403, {"statusCode": "403", "message": "Unauthorized"}),
        # Wrong bucket name: same 404-in-a-400 shape, but a misconfiguration.
        _FakeResponse(
            400,
            {"statusCode": "404", "error": "not_found", "message": "Bucket not found"},
        ),
        # Malformed request with a non-not-found reason.
        _FakeResponse(400, {"statusCode": "400", "message": "Invalid key"}),
        # A 400 that is not even JSON (proxy/CDN error page).
        _FakeResponse(400, None, b"<html>Bad Request</html>"),
        # Server-side failure.
        _FakeResponse(500, {"message": "Internal Server Error"}),
    ],
)
def test_real_supabase_errors_are_not_swallowed(monkeypatch, response):
    import httpx

    backend = _supabase(monkeypatch, response)
    with pytest.raises(httpx.HTTPStatusError):
        backend.image_exists("pid", "car.jpg")


def test_upload_still_generates_unique_names_on_collision(cloud, png_bytes):
    """Collision handling is unchanged: same filename twice => distinct keys."""
    client, fake = cloud
    project = make_project(client, "Collisions")
    pid = project["id"]

    first = upload_png(client, pid, "car.jpg", png_bytes)
    second = upload_png(client, pid, "car.jpg", png_bytes)

    assert first["filename"] == "car.jpg"
    assert second["filename"] != first["filename"]
    assert second["filename"].startswith("car_")
    assert second["filename"].endswith(".jpg")
    # Both blobs exist independently under the project's prefix.
    assert fake.image_exists(pid, first["filename"]) is True
    assert fake.image_exists(pid, second["filename"]) is True
    assert len(client.get(f"/projects/{pid}/images").json()["data"]) == 2


# ---------------------------------------------------------------------------
# Image deletion in cloud mode
#
# The service layer already removed the index entry and the annotations; what
# needed checking was that the *blob* really goes, that a failure is reported
# instead of silently leaving an orphan, and that the blast radius is one object.
# ---------------------------------------------------------------------------

def test_delete_image_removes_blob_index_and_annotations(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Deletions")
    pid = project["id"]

    keep = upload_png(client, pid, "keep.png", png_bytes)
    doomed = upload_png(client, pid, "doomed.png", png_bytes)
    label = make_label(client, pid, "car")
    box = {"x": 1, "y": 2, "width": 3, "height": 4}
    make_annotation(client, pid, doomed["id"], box, label=label)
    make_annotation(client, pid, keep["id"], box, label=label)

    resp = client.delete(f"/projects/{pid}/images/{doomed['id']}")
    assert resp.status_code == 200

    # 1. the object itself is gone from storage, 2. so is the index entry
    assert fake.image_exists(pid, doomed["filename"]) is False
    listed = client.get(f"/projects/{pid}/images").json()["data"]
    assert [img["id"] for img in listed] == [keep["id"]]

    # 3. its annotations are gone; the sibling's survive
    remaining = client.get(f"/projects/{pid}/images/{keep['id']}/annotations")
    assert len(remaining.json()["data"]) == 1
    assert fake.read_doc(pid, "annotations", []) != []

    # 5. the sibling blob is untouched and still servable
    assert fake.image_exists(pid, keep["filename"]) is True
    assert client.get(f"/projects/{pid}/images/{keep['id']}/file").status_code == 200

    # 6. the project itself survives, with consistent counts
    body = client.get(f"/projects/{pid}").json()["data"]
    assert body["images"] == 1
    assert body["annotations"] == 1
    # 7. nothing orphaned: the only image key left belongs to the survivor
    assert [name for (p, name) in fake.images if p == pid] == [keep["filename"]]


def test_deleted_image_stays_deleted_and_is_unservable(cloud, png_bytes):
    """What a page refresh would see, plus a repeated delete."""
    client, fake = cloud
    project = make_project(client, "Persistence")
    pid = project["id"]
    image = upload_png(client, pid, "gone.png", png_bytes)

    assert client.delete(f"/projects/{pid}/images/{image['id']}").status_code == 200

    # Re-reading from storage (what a refresh does) still shows it gone.
    assert client.get(f"/projects/{pid}/images").json()["data"] == []
    assert client.get(f"/projects/{pid}/images/{image['id']}").status_code == 404
    assert client.get(f"/projects/{pid}/images/{image['id']}/file").status_code == 404
    # Deleting twice is a clean 404, not a 500.
    assert client.delete(f"/projects/{pid}/images/{image['id']}").status_code == 404


def test_delete_image_failure_leaves_no_orphan(cloud, png_bytes, monkeypatch):
    """A failed blob delete must keep the index entry so the user can retry."""
    client, fake = cloud
    project = make_project(client, "Failure")
    pid = project["id"]
    image = upload_png(client, pid, "stuck.png", png_bytes)

    def boom(project_id, stored_name):
        raise RuntimeError("supabase unavailable")

    monkeypatch.setattr(fake, "delete_image", boom)

    with pytest.raises(RuntimeError):
        client.delete(f"/projects/{pid}/images/{image['id']}")

    # The entry survived, so the image is still reachable and retryable —
    # rather than an unreachable object stranded in the bucket.
    monkeypatch.undo()
    assert len(client.get(f"/projects/{pid}/images").json()["data"]) == 1
    assert client.delete(f"/projects/{pid}/images/{image['id']}").status_code == 200
    assert fake.image_exists(pid, image["filename"]) is False


def test_supabase_delete_image_targets_exactly_one_key(monkeypatch):
    """The real adapter deletes one object, and cannot widen its own prefix."""
    from app.core.config import settings
    from app.core.storage_backend import SupabaseStorageBackend

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://ref.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "svc-key")
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "projects")
    backend = SupabaseStorageBackend()

    batches: list[list[str]] = []
    monkeypatch.setattr(
        backend, "_delete_keys", lambda keys: (batches.append(list(keys)), len(keys))[1]
    )

    backend.delete_image("pid", "car.jpg")
    assert batches == [["pid/images/car.jpg"]]

    # A traversal attempt is refused outright rather than deleting a wider
    # prefix (which would take the whole project's objects).
    batches.clear()
    for hostile in ("../..", "../metadata.json", "a/b", "", "x\x00y"):
        backend.delete_image("pid", hostile)
    backend.delete_image("../other", "car.jpg")
    assert batches == []


def test_delete_keys_tolerates_already_deleted_object(monkeypatch):
    """Re-deleting a gone object succeeds; real errors still raise."""
    import httpx

    missing = _FakeResponse(
        400, {"statusCode": "404", "error": "not_found", "message": "Object not found"}
    )
    backend = _supabase(monkeypatch, missing)
    assert backend._delete_keys(["pid/images/gone.png"]) == 1  # no raise

    denied = _supabase(monkeypatch, _FakeResponse(401, {"message": "Invalid JWT"}))
    with pytest.raises(httpx.HTTPStatusError):
        denied._delete_keys(["pid/images/gone.png"])

    # An empty batch never touches the network.
    assert backend._delete_keys([]) == 0
