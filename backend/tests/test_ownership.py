"""Anonymous per-browser project ownership tests.

The reported bug: any browser could see and open any project, because projects
were effectively global. The fix gives every browser a cryptographically random
anonymous session id (an HttpOnly cookie, no login), stamps each new project with
the creating session as its ``owner_id``, and makes *every* project-scoped
endpoint refuse a project the calling session does not own — returning the same
404 as a missing project so existence never leaks.

Test model
----------
Ownership is enforced only in the shared public (cloud) deployment; local/
self-hosted mode stays exactly v1.0.0 (unscoped), which is asserted at the end.
The cloud tests therefore run against the in-memory ``FakeCloudBackend`` from
``test_deployment`` with ``STORAGE_BACKEND=cloud``.

Two browsers == two ``TestClient`` instances sharing that one backend, each with
its own cookie jar. They use ``base_url="https://testserver"`` on purpose: the
session cookie is ``Secure``, and httpx's cookie jar will store but NOT resend a
Secure cookie over plain http, which would make every request look like a fresh
browser and mask the very behavior under test.
"""

import pytest

from conftest import (  # noqa: E402  (path set up by conftest)
    make_annotation,
    make_label,
    make_project,
    upload_png,
)
from test_deployment import FakeCloudBackend


# ---------------------------------------------------------------------------
# Fixtures: a cloud backend shared by independently-cookied browsers
# ---------------------------------------------------------------------------

@pytest.fixture
def owned_cloud(tmp_path, monkeypatch):
    """Run the app in ownership-enforcing cloud mode over one shared backend.

    Yields a ``browser()`` factory. Each call returns a *new* ``TestClient``
    (its own cookie jar => a distinct anonymous browser) bound to the same app
    and the same in-memory store, over https so the Secure session cookie is
    actually resent between requests.
    """
    from fastapi.testclient import TestClient

    from app.core import storage_backend
    from app.core.config import settings

    fake = FakeCloudBackend()
    monkeypatch.setattr(storage_backend, "_backend", fake)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloud")
    monkeypatch.setattr(settings, "EXPORT_DIR", tmp_path / "exports")

    # Sanity: this is the mode the bug lives in, so ownership must be ON here.
    assert settings.is_cloud is True
    assert settings.owner_scoping_enabled is True

    from app.main import app

    clients: list[TestClient] = []

    def browser() -> TestClient:
        c = TestClient(app, base_url="https://testserver")
        c.__enter__()
        clients.append(c)
        return c

    try:
        yield browser, fake
    finally:
        for c in clients:
            c.__exit__(None, None, None)


def _prime(client):
    """Ensure the browser has been issued its session cookie.

    The cookie is minted on the first response; priming with a harmless GET means
    later assertions about isolation are not confused by first-request minting.
    """
    client.get("/health")
    return client


# ---------------------------------------------------------------------------
# Test A: a session can create and list its own project
# ---------------------------------------------------------------------------

def test_a_session_creates_and_lists_own_project(owned_cloud):
    browser, _fake = owned_cloud
    a = _prime(browser())

    project = make_project(a, "Project A")

    listed = a.get("/projects").json()["data"]
    assert [p["id"] for p in listed] == [project["id"]]
    # The browser really was given an HttpOnly session cookie.
    assert a.cookies.get("fl_sid")


# ---------------------------------------------------------------------------
# Test B: another session's listing excludes the first session's project
# ---------------------------------------------------------------------------

def test_b_other_session_list_excludes_foreign_project(owned_cloud):
    browser, _fake = owned_cloud
    a = _prime(browser())
    b = _prime(browser())

    project = make_project(a, "Project A")

    # B lists nothing — A's project is invisible to it.
    assert b.get("/projects").json()["data"] == []

    # And the two browsers really do have different identities.
    assert a.cookies.get("fl_sid") != b.cookies.get("fl_sid")

    # B creating its own project does not reveal A's, and vice versa.
    b_project = make_project(b, "Project B")
    assert [p["id"] for p in b.get("/projects").json()["data"]] == [b_project["id"]]
    assert [p["id"] for p in a.get("/projects").json()["data"]] == [project["id"]]


# ---------------------------------------------------------------------------
# Test C: direct project access by a foreign session is rejected (as 404)
# ---------------------------------------------------------------------------

def test_c_direct_project_access_rejected_for_foreign_session(owned_cloud):
    browser, _fake = owned_cloud
    a = _prime(browser())
    b = _prime(browser())

    pid = make_project(a, "Project A")["id"]

    # Every project-metadata verb is refused for B, with a 404 that is byte-for
    # byte the "missing project" response, so B cannot even tell it exists.
    missing = b.get("/projects/does-not-exist-000")
    assert missing.status_code == 404

    assert b.get(f"/projects/{pid}").status_code == 404
    assert b.get(f"/projects/{pid}").json() == missing.json()
    assert b.put(f"/projects/{pid}", json={"name": "hacked"}).status_code == 404
    assert b.delete(f"/projects/{pid}").status_code == 404

    # A's project is untouched (name not changed, still present).
    assert a.get(f"/projects/{pid}").json()["data"]["name"] == "Project A"


# ---------------------------------------------------------------------------
# Test D: every project-scoped sub-resource is refused for a foreign session
# ---------------------------------------------------------------------------

def test_d_all_subresources_rejected_for_foreign_session(owned_cloud, png_bytes):
    browser, _fake = owned_cloud
    a = _prime(browser())
    b = _prime(browser())

    # A builds a fully populated project: image + label + annotation.
    pid = make_project(a, "Project A")["id"]
    image = upload_png(a, pid, "pic.png", png_bytes)
    label = make_label(a, pid, "cat")
    ann = make_annotation(
        a, pid, image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )
    iid, lid, aid = image["id"], label["id"], ann["id"]

    # ---- images ----
    assert b.post(
        f"/projects/{pid}/images",
        files=[("files", ("evil.png", png_bytes, "image/png"))],
    ).status_code == 404
    assert b.get(f"/projects/{pid}/images").status_code == 404
    assert b.get(f"/projects/{pid}/images/{iid}").status_code == 404
    assert b.get(f"/projects/{pid}/images/{iid}/file").status_code == 404
    assert b.delete(f"/projects/{pid}/images/{iid}").status_code == 404

    # ---- labels ----
    assert b.get(f"/projects/{pid}/labels").status_code == 404
    assert b.post(f"/projects/{pid}/labels", json={"name": "dog"}).status_code == 404
    assert b.put(
        f"/projects/{pid}/labels/{lid}", json={"name": "dog"}
    ).status_code == 404
    assert b.delete(f"/projects/{pid}/labels/{lid}").status_code == 404

    # ---- annotations ----
    assert b.get(
        f"/projects/{pid}/images/{iid}/annotations"
    ).status_code == 404
    assert b.post(
        f"/projects/{pid}/images/{iid}/annotations",
        json={"x": 0.1, "y": 0.1, "width": 0.1, "height": 0.1},
    ).status_code == 404
    assert b.put(
        f"/projects/{pid}/images/{iid}/annotations/{aid}",
        json={"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
    ).status_code == 404
    assert b.delete(
        f"/projects/{pid}/images/{iid}/annotations/{aid}"
    ).status_code == 404

    # ---- exports ----
    assert b.get(f"/projects/{pid}/export/yolo").status_code == 404
    assert b.get(f"/projects/{pid}/export/coco").status_code == 404

    # Nothing B attempted mutated A's project: same counts, annotation intact.
    body = a.get(f"/projects/{pid}").json()["data"]
    assert body["images"] == 1 and body["annotations"] == 1
    a_anns = a.get(f"/projects/{pid}/images/{iid}/annotations").json()["data"]
    assert [x["id"] for x in a_anns] == [aid]


# ---------------------------------------------------------------------------
# Test E: the owning session remains fully functional end to end
# ---------------------------------------------------------------------------

def test_e_owner_still_has_full_functionality(owned_cloud, png_bytes):
    browser, _fake = owned_cloud
    a = _prime(browser())

    pid = make_project(a, "Project A")["id"]
    image = upload_png(a, pid, "pic.png", png_bytes)
    label = make_label(a, pid, "cat")
    ann = make_annotation(
        a, pid, image["id"],
        {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}, label,
    )

    # Read back.
    assert a.get(f"/projects/{pid}").status_code == 200
    assert a.get(f"/projects/{pid}/images/{image['id']}/file").content == png_bytes

    # Both exports work for the owner.
    yolo = a.get(f"/projects/{pid}/export/yolo")
    assert yolo.status_code == 200 and yolo.content[:2] == b"PK"
    coco = a.get(f"/projects/{pid}/export/coco")
    assert coco.status_code == 200 and coco.content[:2] == b"PK"

    # Update + delete an annotation, then delete the image, then the project.
    assert a.put(
        f"/projects/{pid}/images/{image['id']}/annotations/{ann['id']}",
        json={"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
    ).status_code == 200
    assert a.delete(
        f"/projects/{pid}/images/{image['id']}/annotations/{ann['id']}"
    ).status_code == 200
    assert a.delete(f"/projects/{pid}/images/{image['id']}").status_code == 200
    assert a.delete(f"/projects/{pid}").status_code == 200
    assert a.get(f"/projects/{pid}").status_code == 404


# ---------------------------------------------------------------------------
# Session-id handling: cookie flags, no body leak, no client override
# ---------------------------------------------------------------------------

def test_session_cookie_is_httponly_secure_samesite_none(owned_cloud):
    browser, _fake = owned_cloud
    a = browser()

    resp = a.get("/health")
    setcookie = resp.headers.get("set-cookie", "")
    assert "fl_sid=" in setcookie
    low = setcookie.lower()
    assert "httponly" in low
    assert "secure" in low
    assert "samesite=none" in low
    assert "path=/" in low


def test_owner_id_never_appears_in_any_response_body(owned_cloud, png_bytes):
    browser, _fake = owned_cloud
    a = _prime(browser())

    created = make_project(a, "Project A")
    assert "owner_id" not in created  # the session id must not leak to JS

    pid = created["id"]
    listed = a.get("/projects").json()["data"]
    assert all("owner_id" not in p for p in listed)
    fetched = a.get(f"/projects/{pid}").json()["data"]
    assert "owner_id" not in fetched
    updated = a.put(f"/projects/{pid}", json={"name": "A2"}).json()["data"]
    assert "owner_id" not in updated

    # The real session id (from the cookie) appears nowhere in the JSON bodies.
    sid = a.cookies.get("fl_sid")
    assert sid
    for text in (
        a.get("/projects").text,
        a.get(f"/projects/{pid}").text,
    ):
        assert sid not in text


def test_client_cannot_claim_ownership_via_request_body(owned_cloud):
    """An ``owner_id`` sent in the body is ignored; the cookie decides ownership.

    B tries to create a project while *supplying* an ``owner_id`` in the JSON
    body (a spoof attempt). It is dropped (ProjectCreate ignores extra keys), the
    project is owned by B's cookie session, and A — even sending the same forged
    ``owner_id`` — cannot see or open it.
    """
    browser, _fake = owned_cloud
    a = _prime(browser())
    b = _prime(browser())

    forged = "attacker-supplied-owner-value-aaaaaaaaaaaaaaaa"
    resp = b.post("/projects", json={"name": "B", "owner_id": forged})
    assert resp.status_code == 201
    pid = resp.json()["data"]["id"]

    # A cannot reach it by resending the same forged id in the body.
    assert a.put(
        f"/projects/{pid}", json={"name": "hijack", "owner_id": forged}
    ).status_code == 404
    assert a.get(f"/projects/{pid}").status_code == 404
    # B still owns it.
    assert b.get(f"/projects/{pid}").status_code == 200


def test_legacy_ownerless_project_is_not_claimable_in_cloud(owned_cloud):
    """A project stored before ownership existed (no owner_id) belongs to nobody.

    It must not be silently handed to whoever asks first, so every session gets a
    404 for it — while it remains present in the store (a migration decision, not
    data loss).
    """
    browser, fake = owned_cloud
    a = _prime(browser())

    # Simulate a pre-migration project written directly to the store.
    legacy_id = "legacy-project-0001"
    fake.write_doc(legacy_id, "metadata", {
        "id": legacy_id,
        "name": "Legacy",
        "status": "active",
        # no owner_id, no expires_at (as old metadata had)
    })
    fake.write_doc(legacy_id, "images", [])
    fake.write_doc(legacy_id, "labels", [])
    fake.write_doc(legacy_id, "annotations", [])

    assert a.get(f"/projects/{legacy_id}").status_code == 404
    assert legacy_id not in [p["id"] for p in a.get("/projects").json()["data"]]
    # Still physically present — not destroyed, just unowned.
    assert (legacy_id, "metadata") in fake.docs


# ---------------------------------------------------------------------------
# Test F: local/self-hosted mode is unchanged (v1.0.0 behavior preserved)
# ---------------------------------------------------------------------------

def test_f_local_mode_is_unscoped_like_v1(client, png_bytes):
    """In local mode ownership is disabled: the single-user app is unaffected.

    Two clients (which in cloud mode would be two browsers) both see and use the
    same project, exactly as v1.0.0 did, because a self-hosted instance is a
    single trusted user and must not start hiding their own projects from them.
    """
    from app.core.config import settings
    from fastapi.testclient import TestClient
    from app.main import app

    assert settings.is_cloud is False
    assert settings.owner_scoping_enabled is False

    project = make_project(client, "Local")
    upload_png(client, project["id"], "pic.png", png_bytes)

    # A second, independently-cookied client still sees and can open it.
    with TestClient(app) as other:
        listed = other.get("/projects").json()["data"]
        assert any(p["id"] == project["id"] for p in listed)
        assert other.get(f"/projects/{project['id']}").status_code == 200
        assert len(other.get(f"/projects/{project['id']}/images").json()["data"]) == 1


def test_owns_helper_matrix():
    """Unit-level truth table for ProjectManager.owns under both policies."""
    from app.core.config import settings
    from app.models.project import Project
    from app.services.project.manager import manager

    mine = Project(name="mine", owner_id="sid-123")
    legacy = Project(name="legacy", owner_id=None)

    # Local/unscoped: everything is owned (single trusted user).
    assert settings.owner_scoping_enabled is False
    assert manager.owns(mine, "sid-123") is True
    assert manager.owns(mine, "someone-else") is True
    assert manager.owns(legacy, None) is True
