"""Regression tests: labels and annotations.

Covers label create/list, duplicate rejection (409), annotation create/
update/delete, and invalid-input handling (404 for unknown ids, 400 for a
zero-size bounding box).
"""

from conftest import make_annotation, make_label, make_project, upload_png


# -----------------------
# Labels
# -----------------------

def test_create_and_list_labels(client):
    project = make_project(client)
    car = make_label(client, project["id"], "car", color="#ff0000")
    assert car["name"] == "car"
    assert car["color"] == "#ff0000"

    make_label(client, project["id"], "person")

    listed = client.get(f"/projects/{project['id']}/labels")
    assert listed.status_code == 200
    names = {label["name"] for label in listed.json()["data"]}
    assert names == {"car", "person"}


def test_duplicate_label_is_rejected_with_409(client):
    project = make_project(client)
    make_label(client, project["id"], "car")

    # Same name (case-insensitive) must be rejected.
    resp = client.post(f"/projects/{project['id']}/labels", json={"name": "CAR"})
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "already exists" in body["message"].lower()


def test_create_label_unknown_project_returns_404(client):
    resp = client.post("/projects/nope/labels", json={"name": "car"})
    assert resp.status_code == 404


def test_update_label(client):
    project = make_project(client)
    car = make_label(client, project["id"], "car")
    resp = client.put(
        f"/projects/{project['id']}/labels/{car['id']}",
        json={"name": "vehicle"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "vehicle"


def test_delete_label(client):
    project = make_project(client)
    car = make_label(client, project["id"], "car")
    resp = client.delete(f"/projects/{project['id']}/labels/{car['id']}")
    assert resp.status_code == 200
    # Gone -> second delete 404s.
    assert client.delete(
        f"/projects/{project['id']}/labels/{car['id']}"
    ).status_code == 404


# -----------------------
# Annotations
# -----------------------

BOX = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}


def test_create_list_annotation(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")

    ann = make_annotation(client, project["id"], image["id"], BOX, label=car)
    assert ann["label_id"] == car["id"]
    assert ann["label"] == "car"
    assert ann["x"] == 0.1 and ann["width"] == 0.4

    listed = client.get(
        f"/projects/{project['id']}/images/{image['id']}/annotations"
    )
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == ann["id"]


def test_annotation_reflected_in_project_count(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    make_annotation(client, project["id"], image["id"], BOX)

    refreshed = client.get(f"/projects/{project['id']}").json()["data"]
    assert refreshed["annotations"] == 1


def test_update_annotation(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    ann = make_annotation(client, project["id"], image["id"], BOX)

    new_box = {"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.2, "label": "moved"}
    resp = client.put(
        f"/projects/{project['id']}/images/{image['id']}/annotations/{ann['id']}",
        json=new_box,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["x"] == 0.5 and data["width"] == 0.2
    assert data["label"] == "moved"


def test_delete_annotation(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    ann = make_annotation(client, project["id"], image["id"], BOX)

    resp = client.delete(
        f"/projects/{project['id']}/images/{image['id']}/annotations/{ann['id']}"
    )
    assert resp.status_code == 200
    # List is now empty and project count is back to 0.
    remaining = client.get(
        f"/projects/{project['id']}/images/{image['id']}/annotations"
    ).json()["data"]
    assert remaining == []
    assert client.get(f"/projects/{project['id']}").json()["data"]["annotations"] == 0


def test_create_annotation_unknown_image_returns_404(client):
    project = make_project(client)
    resp = client.post(
        f"/projects/{project['id']}/images/nope/annotations",
        json=BOX,
    )
    assert resp.status_code == 404


def test_create_annotation_zero_size_returns_400(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    resp = client.post(
        f"/projects/{project['id']}/images/{image['id']}/annotations",
        json={"x": 0.1, "y": 0.1, "width": 0.0, "height": 0.2},
    )
    assert resp.status_code == 400
    assert resp.json()["success"] is False


def test_update_unknown_annotation_returns_404(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    resp = client.put(
        f"/projects/{project['id']}/images/{image['id']}/annotations/nope",
        json=BOX,
    )
    assert resp.status_code == 404


def test_delete_unknown_annotation_returns_404(client, png_bytes):
    project = make_project(client)
    image = upload_png(client, project["id"], "car.png", png_bytes)
    resp = client.delete(
        f"/projects/{project['id']}/images/{image['id']}/annotations/nope"
    )
    assert resp.status_code == 404
