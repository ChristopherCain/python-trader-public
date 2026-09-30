"""Temporary-project TTL tests (30-hour lifetime, cloud deployment only).

The public deployment runs on free-tier infrastructure, so a public project is
*disposable*: the server stamps a deadline at creation and the project — plus
every object belonging to it — is permanently deleted once that deadline passes.

Two invariants are load-bearing and are asserted from several angles here:

* **Server authority.** ``expires_at`` is stamped from the server clock at
  creation and stored in metadata. A request body cannot set it, a later config
  change cannot move an existing deadline, and no browser clock participates in
  the decision.
* **Local mode is untouched.** Nothing expires and no destructive cleanup can
  run when ``STORAGE_BACKEND`` is local, so a self-hosted install keeps v1.0.0
  behavior exactly.

The cloud path runs against the in-memory ``FakeCloudBackend`` from
``test_deployment``, so the whole FastAPI stack is exercised with no network.
"""

from datetime import datetime, timedelta, timezone

import pytest

from conftest import make_annotation, make_label, make_project, upload_png
from test_deployment import FakeCloudBackend, cloud  # noqa: F401  (fixture reuse)

TTL_HOURS = 30


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _meta(fake, project_id):
    return fake.docs[(project_id, "metadata")]


def _parse(value):
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _age_past_deadline(fake, project_id, hours=TTL_HOURS + 1):
    """Rewind a project's stored timestamps so its deadline has passed.

    This is the only way to expire a project in a test: the deadline is stored,
    server-stamped metadata, so there is no API that can move it.
    """
    meta = _meta(fake, project_id)
    aged = datetime.now(timezone.utc) - timedelta(hours=hours)
    meta["created_at"] = aged.isoformat()
    meta["expires_at"] = (aged + timedelta(hours=TTL_HOURS)).isoformat()
    return meta


def _keys(fake, project_id):
    """Every object the fake backend holds for one project."""
    return (
        [k for k in fake.docs if k[0] == project_id]
        + [k for k in fake.images if k[0] == project_id]
    )


# ---------------------------------------------------------------------------
# 1-3. Timestamps are server-generated and not client-controllable
# ---------------------------------------------------------------------------

def test_created_at_is_server_generated(cloud):
    client, _fake = cloud
    before = datetime.now(timezone.utc) - timedelta(seconds=5)
    project = make_project(client, "Stamped")
    after = datetime.now(timezone.utc) + timedelta(seconds=5)

    created = _parse(project["created_at"])
    assert before <= created <= after


def test_expires_at_is_exactly_30_hours_after_created_at(cloud):
    client, _fake = cloud
    project = make_project(client, "Deadline")

    created = _parse(project["created_at"])
    expires = _parse(project["expires_at"])
    assert expires - created == timedelta(hours=TTL_HOURS)


def test_frontend_cannot_control_expires_at(cloud):
    """A client-supplied deadline (or creation time) is ignored, not honored."""
    client, _fake = cloud
    forged_expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    forged_created = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

    resp = client.post(
        "/projects",
        json={
            "name": "Forged",
            "expires_at": forged_expiry,
            "created_at": forged_created,
            "seconds_remaining": 999999,
        },
    )
    assert resp.status_code == 201
    project = resp.json()["data"]

    assert project["expires_at"] != forged_expiry
    assert project["created_at"] != forged_created
    created = _parse(project["created_at"])
    assert _parse(project["expires_at"]) - created == timedelta(hours=TTL_HOURS)
    # And the countdown is bounded by the real TTL, not the forged number.
    assert 0 < project["seconds_remaining"] <= TTL_HOURS * 3600


def test_update_cannot_extend_the_deadline(cloud):
    """PUT /projects/{id} carries no timestamp field, so lifetime is fixed."""
    client, _fake = cloud
    project = make_project(client, "Fixed")
    original = project["expires_at"]

    resp = client.put(
        f"/projects/{project['id']}",
        json={
            "name": "Renamed",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=99)).isoformat(),
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["name"] == "Renamed"
    assert updated["expires_at"] == original


# ---------------------------------------------------------------------------
# 4-5. Valid before the deadline, expired after it
# ---------------------------------------------------------------------------

def test_project_is_valid_before_the_deadline(cloud):
    client, fake = cloud
    project = make_project(client, "Young")
    # 29 hours old: still inside the 30-hour window.
    _age_past_deadline(fake, project["id"], hours=29)

    resp = client.get(f"/projects/{project['id']}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert 0 < data["seconds_remaining"] <= 3600


def test_project_is_expired_after_the_deadline(cloud):
    client, fake = cloud
    project = make_project(client, "Old")
    _age_past_deadline(fake, project["id"])

    from app.services.project.manager import manager as project_manager
    from app.models.project import Project

    stored = Project(**_meta(fake, project["id"]))
    assert project_manager.is_expired(stored) is True


def test_expiry_is_judged_on_stored_deadline_not_current_config(cloud, monkeypatch):
    """Editing the TTL setting later must not move an existing deadline."""
    client, fake = cloud
    from app.core.config import settings

    project = make_project(client, "Stable")
    original = _meta(fake, project["id"])["expires_at"]

    monkeypatch.setattr(settings, "PROJECT_TTL_HOURS", 1)
    assert _meta(fake, project["id"])["expires_at"] == original
    assert client.get(f"/projects/{project['id']}").status_code == 200


# ---------------------------------------------------------------------------
# 6-11. Every project-scoped endpoint refuses an expired project
# ---------------------------------------------------------------------------

def test_expired_project_is_not_listed(cloud):
    client, fake = cloud
    fresh = make_project(client, "Fresh")
    old = make_project(client, "Old")
    _age_past_deadline(fake, old["id"])

    listed = {p["id"] for p in client.get("/projects").json()["data"]}
    assert fresh["id"] in listed
    assert old["id"] not in listed


def test_expired_project_cannot_be_opened(cloud):
    client, fake = cloud
    project = make_project(client, "Gone")
    _age_past_deadline(fake, project["id"])

    resp = client.get(f"/projects/{project['id']}")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_expired_project_images_cannot_be_served(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Images")
    image = upload_png(client, project["id"], "pic.png", png_bytes)
    _age_past_deadline(fake, project["id"])

    pid, iid = project["id"], image["id"]
    assert client.get(f"/projects/{pid}/images").status_code == 404
    assert client.get(f"/projects/{pid}/images/{iid}").status_code == 404
    assert client.get(f"/projects/{pid}/images/{iid}/file").status_code == 404
    assert client.delete(f"/projects/{pid}/images/{iid}").status_code == 404
    # Uploading into an expired project is refused too.
    resp = client.post(
        f"/projects/{pid}/images",
        files=[("files", ("new.png", png_bytes, "image/png"))],
    )
    assert resp.status_code == 404


def test_expired_project_annotations_cannot_be_modified(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Anns")
    pid = project["id"]
    image = upload_png(client, pid, "pic.png", png_bytes)
    label = make_label(client, pid, "cat")
    box = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}
    annotation = make_annotation(client, pid, image["id"], box, label)
    _age_past_deadline(fake, pid)

    iid, aid = image["id"], annotation["id"]
    base = f"/projects/{pid}/images/{iid}/annotations"
    assert client.get(base).status_code == 404
    assert client.post(base, json=box).status_code == 404
    assert client.put(f"{base}/{aid}", json=box).status_code == 404
    assert client.delete(f"{base}/{aid}").status_code == 404


def test_expired_project_labels_cannot_be_modified(cloud):
    client, fake = cloud
    project = make_project(client, "Labels")
    pid = project["id"]
    label = make_label(client, pid, "cat")
    _age_past_deadline(fake, pid)

    assert client.get(f"/projects/{pid}/labels").status_code == 404
    assert client.post(f"/projects/{pid}/labels", json={"name": "dog"}).status_code == 404
    resp = client.put(f"/projects/{pid}/labels/{label['id']}", json={"name": "dog"})
    assert resp.status_code == 404
    assert client.delete(f"/projects/{pid}/labels/{label['id']}").status_code == 404


def test_expired_project_cannot_be_exported(cloud, png_bytes):
    client, fake = cloud
    project = make_project(client, "Export")
    pid = project["id"]
    upload_png(client, pid, "pic.png", png_bytes)
    _age_past_deadline(fake, pid)

    resp = client.get(f"/projects/{pid}/export/yolo")
    assert resp.status_code == 404


def test_expired_project_predict_and_delete_are_refused(cloud, png_bytes):
    """The remaining project-scoped routes respect the TTL as well."""
    client, fake = cloud
    project = make_project(client, "Rest")
    pid = project["id"]
    image = upload_png(client, pid, "pic.png", png_bytes)
    _age_past_deadline(fake, pid)

    assert client.post(f"/projects/{pid}/images/{image['id']}/predict").status_code == 404
    # Deleting reports not-found as well: the sweep owns its removal.
    assert client.delete(f"/projects/{pid}").status_code == 404


# ---------------------------------------------------------------------------
# 12-15. Cleanup: complete, scoped, idempotent, never destructive locally
# ---------------------------------------------------------------------------

def test_cleanup_deletes_every_object_of_an_expired_project(cloud, png_bytes):
    client, fake = cloud
    from app.services.project.manager import manager as project_manager

    project = make_project(client, "Doomed")
    pid = project["id"]
    image = upload_png(client, pid, "pic.png", png_bytes)
    label = make_label(client, pid, "cat")
    make_annotation(
        client, pid, image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )

    # Everything the project owns exists first: all four docs plus the blob.
    assert (pid, "metadata") in fake.docs
    assert (pid, "images") in fake.docs
    assert (pid, "labels") in fake.docs
    assert (pid, "annotations") in fake.docs
    assert fake.image_exists(pid, image["filename"])

    _age_past_deadline(fake, pid)
    result = project_manager.cleanup_expired_projects()

    assert result["enabled"] is True
    assert result["deleted"] == 1
    assert result["failed"] == 0
    # Nothing recoverable remains: no docs, no blobs, no key of any kind.
    assert _keys(fake, pid) == []
    assert fake.read_doc(pid, "metadata", None) is None
    assert fake.read_image_bytes(pid, image["filename"]) is None


def test_cleanup_does_not_delete_another_projects_objects(cloud, png_bytes):
    client, fake = cloud
    from app.services.project.manager import manager as project_manager

    doomed = make_project(client, "Doomed")
    keeper = make_project(client, "Keeper")
    keeper_image = upload_png(client, keeper["id"], "keep.png", png_bytes)

    _age_past_deadline(fake, doomed["id"])
    result = project_manager.cleanup_expired_projects()

    assert result["deleted"] == 1
    assert _keys(fake, doomed["id"]) == []
    # The healthy project is completely untouched and still fully usable.
    assert (keeper["id"], "metadata") in fake.docs
    assert fake.image_exists(keeper["id"], keeper_image["filename"])
    assert client.get(f"/projects/{keeper['id']}").status_code == 200


def test_supabase_delete_is_prefix_scoped_and_ordered(monkeypatch):
    """The real adapter never touches an id that merely shares a prefix.

    Also pins the deletion *order*: payload objects first and ``metadata.json``
    last, so a partial failure leaves the project discoverable-and-expired for
    the next sweep instead of orphaning unreachable blobs.
    """
    from app.core.config import settings
    from app.core.storage_backend import SupabaseStorageBackend

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://ref.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "svc-key")
    backend = SupabaseStorageBackend()

    # "abc" is the target; "abcdef" is a different project sharing the prefix.
    listed = [
        "abc/metadata.json",
        "abc/images.json",
        "abc/labels.json",
        "abc/annotations.json",
        "abc/images/pic.png",
        "abcdef/metadata.json",
        "abcdef/images/other.png",
    ]
    batches: list[list[str]] = []
    monkeypatch.setattr(backend, "_list_keys", lambda prefix: list(listed))
    monkeypatch.setattr(
        backend, "_delete_keys", lambda keys: (batches.append(list(keys)), len(keys))[1]
    )

    assert backend.delete_project("abc") is True

    removed = [key for batch in batches for key in batch]
    # Scoped: only the target project's keys, never the prefix-sharing neighbour.
    assert set(removed) == {
        "abc/metadata.json",
        "abc/images.json",
        "abc/labels.json",
        "abc/annotations.json",
        "abc/images/pic.png",
    }
    assert not any(key.startswith("abcdef/") for key in removed)
    # Ordered: metadata.json is the very last key removed.
    assert removed[-1] == "abc/metadata.json"
    assert batches[-1] == ["abc/metadata.json"]


def test_cleanup_is_idempotent(cloud, png_bytes):
    client, fake = cloud
    from app.services.project.manager import manager as project_manager

    project = make_project(client, "Twice")
    upload_png(client, project["id"], "pic.png", png_bytes)
    _age_past_deadline(fake, project["id"])

    first = project_manager.cleanup_expired_projects()
    second = project_manager.cleanup_expired_projects()
    third = project_manager.cleanup_expired_projects()

    assert first["deleted"] == 1
    # Converges: repeated runs are safe no-ops rather than errors.
    assert second["deleted"] == 0
    assert third["deleted"] == 0
    assert second["failed"] == 0 and third["failed"] == 0
    assert _keys(fake, project["id"]) == []


def test_cleanup_never_runs_destructive_deletion_in_local_mode(client, png_bytes, monkeypatch):
    """Local mode: no expiry stamped, and the sweep cannot delete anything.

    ``backend.delete_project`` is replaced with a tripwire, so the assertion is
    not merely "the project survived" but "no destructive call was even made".
    """
    from app.core.config import settings
    from app.core.storage_backend import get_backend
    from app.services.project.manager import manager as project_manager

    assert settings.is_cloud is False
    assert settings.project_ttl_enabled is False

    project = make_project(client, "Self-hosted")
    upload_png(client, project["id"], "pic.png", png_bytes)
    # No deadline is stamped at all, so nothing can ever expire locally.
    assert project["expires_at"] is None
    assert project["seconds_remaining"] is None

    calls: list[str] = []
    monkeypatch.setattr(
        type(get_backend()),
        "delete_project",
        lambda self, pid: calls.append(pid) or True,
    )

    result = project_manager.cleanup_expired_projects()
    assert result == {"enabled": False, "deleted": 0, "checked": 0, "failed": 0}
    assert calls == []
    # Still fully usable afterwards.
    assert client.get(f"/projects/{project['id']}").status_code == 200


def test_cleanup_ignores_projects_still_inside_their_window(cloud):
    client, fake = cloud
    from app.services.project.manager import manager as project_manager

    project = make_project(client, "Young")
    _age_past_deadline(fake, project["id"], hours=29)

    result = project_manager.cleanup_expired_projects()
    assert result["checked"] == 1
    assert result["deleted"] == 0
    assert client.get(f"/projects/{project['id']}").status_code == 200


# ---------------------------------------------------------------------------
# Countdown surface: server-computed, advisory only
# ---------------------------------------------------------------------------

def test_seconds_remaining_is_server_computed(cloud):
    client, _fake = cloud
    project = make_project(client, "Countdown")

    # Fresh project: just under the full window, never above it.
    assert TTL_HOURS * 3600 - 60 <= project["seconds_remaining"] <= TTL_HOURS * 3600
    listed = client.get("/projects").json()["data"][0]
    assert listed["seconds_remaining"] is not None


def test_countdown_cannot_extend_the_server_side_expiration(cloud):
    """No request can move the deadline the server will actually enforce."""
    client, fake = cloud
    project = make_project(client, "Immutable")
    pid = project["id"]
    stored = _meta(fake, pid)["expires_at"]

    # Every plausible client attempt: create-time forgery, update, re-open.
    client.put(
        f"/projects/{pid}",
        json={"name": "x", "seconds_remaining": 10 ** 9, "expires_at": None},
    )
    client.get(f"/projects/{pid}")
    assert _meta(fake, pid)["expires_at"] == stored

    # And once the stored deadline passes, the project is gone regardless of
    # anything the client believes about the countdown.
    _age_past_deadline(fake, pid)
    assert client.get(f"/projects/{pid}").status_code == 404


def test_config_endpoint_advertises_ttl(cloud):
    client, _fake = cloud
    data = client.get("/config").json()["data"]
    assert data["temporary_projects"] is True
    assert data["project_ttl_hours"] == TTL_HOURS


def test_config_endpoint_reports_permanent_projects_locally(client):
    data = client.get("/config").json()["data"]
    assert data["temporary_projects"] is False
    assert data["project_ttl_hours"] is None


# ---------------------------------------------------------------------------
# 16-17. Frontend surfaces the lifetime (asserted against the shipped source)
# ---------------------------------------------------------------------------

FRONTEND_SRC = (
    __import__("pathlib").Path(__file__).resolve().parents[2] / "frontend" / "src"
)


def _source(*parts):
    path = FRONTEND_SRC.joinpath(*parts)
    if not path.exists():  # pragma: no cover - guards a moved file
        pytest.skip(f"frontend source not present: {path}")
    return path.read_text(encoding="utf-8")


def test_creation_ui_shows_the_30_hour_warning():
    """The create flow must state the lifetime, the loss, and the export advice."""
    source = _source("components", "CreateProjectModal.jsx")

    assert "Temporary Project" in source
    assert "permanently deleted" in source
    # Copy is driven by the server-advertised TTL rather than a hard-coded 30.
    assert "ttlHours" in source
    assert "images, annotations, labels" in source.lower()
    assert "export your dataset" in source.lower()
    # No browser dialogs anywhere in the flow.
    assert "alert(" not in source


def test_project_card_shows_remaining_lifetime():
    card = _source("components", "ProjectCard.jsx")
    badge = _source("components", "ExpiryBadge.jsx")

    # The card renders the badge from the server's countdown field.
    assert "ExpiryBadge" in card
    assert "seconds_remaining" in card
    # The badge renders "Expires in <time>" and escalates as the deadline nears.
    assert "Expires in" in badge
    assert "urgent" in badge or "urgent" in _source("utils", "expiry.js")
    # It disappears entirely when the server sends no deadline (local mode).
    assert "null" in badge or "return null" in badge


def test_expiry_formatting_helper_is_hour_and_minute_based():
    helper = _source("utils", "expiry.js")
    assert "formatRemaining" in helper
    assert "h ${minutes}m" in helper
    # Tone thresholds exist so the indicator gets louder near the deadline.
    assert "expiryTone" in helper
