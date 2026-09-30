"""Regression test: persistence round-trip across a simulated restart.

The MVP's core promise is that the on-disk JSON is the source of truth and
survives a backend restart. We create data through one TestClient, then build a
*second* TestClient over the same isolated storage dir (a fresh app instance =
a process restart) and confirm everything is still readable and consistent.
"""

from conftest import make_annotation, make_label, make_project, upload_png

BOX = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}


def _fresh_client():
    """A brand-new TestClient over the already-isolated storage dir.

    ``isolated_storage`` (autouse) has already repointed ``settings`` for this
    test, so a new app instance reads the same tmp folders — i.e. a restart.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_data_survives_restart(client, png_bytes):
    project = make_project(client, "Persisted")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    ann = make_annotation(client, project["id"], image["id"], BOX, label=car)

    # Simulate a restart: new app/client, same on-disk storage.
    with _fresh_client() as restarted:
        proj = restarted.get(f"/projects/{project['id']}")
        assert proj.status_code == 200
        pdata = proj.json()["data"]
        assert pdata["name"] == "Persisted"
        assert pdata["images"] == 1
        assert pdata["annotations"] == 1

        images = restarted.get(f"/projects/{project['id']}/images").json()["data"]
        assert [i["id"] for i in images] == [image["id"]]

        labels = restarted.get(f"/projects/{project['id']}/labels").json()["data"]
        assert [label["id"] for label in labels] == [car["id"]]

        anns = restarted.get(
            f"/projects/{project['id']}/images/{image['id']}/annotations"
        ).json()["data"]
        assert len(anns) == 1
        assert anns[0]["id"] == ann["id"]
        assert anns[0]["x"] == 0.1 and anns[0]["width"] == 0.4


def test_project_appears_in_list_after_restart(client):
    project = make_project(client, "StillHere")
    with _fresh_client() as restarted:
        ids = {p["id"] for p in restarted.get("/projects").json()["data"]}
        assert project["id"] in ids
