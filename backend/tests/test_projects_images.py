"""Regression tests: project lifecycle and image upload/list.

These lock in the current MVP contract for the project and image endpoints,
including the response envelope shape and invalid-id (404) handling.
"""

from conftest import make_project, upload_png


# -----------------------
# Projects
# -----------------------

def test_create_project_returns_201_and_envelope(client):
    resp = client.post("/projects", json={"name": "Cars"})
    assert resp.status_code == 201
    body = resp.json()
    # Response envelope contract: {success, message, data}.
    assert body["success"] is True
    assert "message" in body
    data = body["data"]
    assert data["name"] == "Cars"
    assert data["id"]
    # A brand-new project starts empty.
    assert data["images"] == 0
    assert data["annotations"] == 0
    assert data["status"] == "active"


def test_create_project_without_name_defaults(client):
    # POST /projects accepts an empty/omitted body (ProjectCreate | None).
    resp = client.post("/projects")
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "Untitled Project"


def test_list_projects_returns_created_projects(client):
    a = make_project(client, "Alpha")
    b = make_project(client, "Beta")

    resp = client.get("/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    ids = {p["id"] for p in body["data"]}
    assert {a["id"], b["id"]} <= ids


def test_get_project_unknown_id_returns_404(client):
    resp = client.get("/projects/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    # Error envelope carries an `error` key (not `data`).
    assert "error" in body


def test_update_project_name(client):
    project = make_project(client, "Before")
    resp = client.put(f"/projects/{project['id']}", json={"name": "After"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "After"


def test_update_unknown_project_returns_404(client):
    resp = client.put("/projects/nope", json={"name": "x"})
    assert resp.status_code == 404


def test_delete_project(client):
    project = make_project(client, "Temp")
    resp = client.delete(f"/projects/{project['id']}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    # It is really gone.
    assert client.get(f"/projects/{project['id']}").status_code == 404


def test_delete_unknown_project_returns_404(client):
    assert client.delete("/projects/nope").status_code == 404


# -----------------------
# Images
# -----------------------

def test_upload_image_and_list(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)

    assert image["filename"].endswith(".png")
    assert image["original_filename"] == "car.png"
    assert image["size"] > 0

    listed = client.get(f"/projects/{project['id']}/images")
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == image["id"]


def test_upload_reflected_in_project_count(client, png_bytes):
    project = make_project(client)
    upload_png(client, project["id"], "a.png", png_bytes)
    upload_png(client, project["id"], "b.png", png_bytes)

    refreshed = client.get(f"/projects/{project['id']}").json()["data"]
    assert refreshed["images"] == 2


def test_upload_unsupported_type_is_skipped_with_400(client):
    project = make_project(client)
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    # No images uploaded + something skipped => 400 with skipped details.
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["skipped"]


def test_upload_to_unknown_project_returns_404(client, png_bytes):
    resp = client.post(
        "/projects/nope/images",
        files=[("files", ("car.png", png_bytes, "image/png"))],
    )
    assert resp.status_code == 404


def test_list_images_unknown_project_returns_404(client):
    assert client.get("/projects/nope/images").status_code == 404


def test_get_and_delete_image(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)

    got = client.get(f"/projects/{project['id']}/images/{image['id']}")
    assert got.status_code == 200
    assert got.json()["data"]["id"] == image["id"]

    deleted = client.delete(f"/projects/{project['id']}/images/{image['id']}")
    assert deleted.status_code == 200
    # Second delete now 404s.
    assert client.delete(
        f"/projects/{project['id']}/images/{image['id']}"
    ).status_code == 404


def test_get_unknown_image_returns_404(client):
    project = make_project(client)
    assert client.get(
        f"/projects/{project['id']}/images/nope"
    ).status_code == 404
