"""Regression tests for M1 — Core Data/Model/API hardening.

Each test locks in one M1 behavior. These are additive: the M0 suite still
pins the untouched happy-path contract, and these pin the new guarantees.

M1 scope covered here:
  1. Label deletion is blocked while annotations reference the label.
  2. Annotation label name resolves from ``label_id`` (no stale name on rename).
  3. YOLO export surfaces orphan/unlabeled boxes instead of silently dropping.
  4. Project counts stay correct after the per-file upload refresh was removed.
  5. Request-validation errors use the standard {success,message,error} envelope.
  6. Unsafe / path-traversal ids are treated as not-found and never touch disk.
"""

import io
import zipfile

from conftest import make_annotation, make_label, make_project, upload_png

BOX = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}


# ---------------------------------------------------------------------------
# 1. Label deletion integrity
# ---------------------------------------------------------------------------

def test_delete_label_blocked_while_referenced(client, png_bytes):
    project = make_project(client, "LabelInUse")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    ann = make_annotation(client, project["id"], image["id"], BOX, label=car)

    resp = client.delete(f"/projects/{project['id']}/labels/{car['id']}")
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "cannot be deleted" in body["message"].lower()
    assert body["error"]["annotation_count"] == 1

    # The label is still there (not silently removed).
    labels = client.get(f"/projects/{project['id']}/labels").json()["data"]
    assert car["id"] in {label["id"] for label in labels}

    # After the referencing annotation is removed, deletion succeeds.
    client.delete(
        f"/projects/{project['id']}/images/{image['id']}/annotations/{ann['id']}"
    )
    ok = client.delete(f"/projects/{project['id']}/labels/{car['id']}")
    assert ok.status_code == 200
    assert ok.json()["success"] is True


def test_delete_unused_label_still_succeeds(client):
    project = make_project(client, "UnusedLabel")
    car = make_label(client, project["id"], "car")
    resp = client.delete(f"/projects/{project['id']}/labels/{car['id']}")
    assert resp.status_code == 200


def test_delete_unknown_label_returns_404(client):
    project = make_project(client, "NoSuchLabel")
    resp = client.delete(f"/projects/{project['id']}/labels/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. Single source of truth for label names
# ---------------------------------------------------------------------------

def test_annotation_label_follows_rename(client, png_bytes):
    project = make_project(client, "Rename")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    make_annotation(client, project["id"], image["id"], BOX, label=car)

    # Rename the label.
    renamed = client.put(
        f"/projects/{project['id']}/labels/{car['id']}",
        json={"name": "vehicle"},
    )
    assert renamed.status_code == 200

    # The annotation now reports the *current* label name, not the stale one.
    anns = client.get(
        f"/projects/{project['id']}/images/{image['id']}/annotations"
    ).json()["data"]
    assert len(anns) == 1
    assert anns[0]["label"] == "vehicle"
    assert anns[0]["label_id"] == car["id"]


def test_orphan_annotation_keeps_stored_label_string(client, png_bytes):
    """An id that no label owns can't be resolved, so the stored string stays."""
    project = make_project(client, "OrphanName")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    client.post(
        f"/projects/{project['id']}/images/{image['id']}/annotations",
        json={**BOX, "label_id": "ghost-label", "label": "ghost"},
    )
    anns = client.get(
        f"/projects/{project['id']}/images/{image['id']}/annotations"
    ).json()["data"]
    assert anns[0]["label"] == "ghost"


# ---------------------------------------------------------------------------
# 3. Orphan-safe export
# ---------------------------------------------------------------------------

def _export_zip(client, project_id):
    resp = client.get(f"/projects/{project_id}/export/yolo")
    assert resp.status_code == 200, resp.text
    return zipfile.ZipFile(io.BytesIO(resp.content))


def test_export_reports_orphan_boxes(client, png_bytes):
    project = make_project(client, "OrphanExport")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")

    # One valid box + one orphan box on the same image.
    make_annotation(client, project["id"], image["id"], BOX, label=car)
    client.post(
        f"/projects/{project['id']}/images/{image['id']}/annotations",
        json={"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.2,
              "label_id": "ghost-label", "label": "ghost"},
    )

    stem = image["filename"].rsplit(".", 1)[0]
    with _export_zip(client, project["id"]) as zf:
        names = set(zf.namelist())
        # The orphan is surfaced in a report file...
        assert "dataset/unlabeled.txt" in names
        report = zf.read("dataset/unlabeled.txt").decode("utf-8")
        assert image["filename"] in report
        assert "total_skipped\t1" in report.replace("\r\n", "\n")

        # ...while the valid box still exports normally (class 0).
        label_txt = zf.read(f"dataset/labels/{stem}.txt").decode("utf-8")
        assert label_txt.replace("\r\n", "\n") == "0 0.300000 0.350000 0.400000 0.300000\n"


def test_export_fully_labeled_has_no_report(client, png_bytes):
    """A clean dataset must still export a pristine YOLO structure."""
    project = make_project(client, "CleanExport")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    make_annotation(client, project["id"], image["id"], BOX, label=car)

    with _export_zip(client, project["id"]) as zf:
        assert "dataset/unlabeled.txt" not in set(zf.namelist())


# ---------------------------------------------------------------------------
# 4. Counts performance (behavior preserved after removing per-file refresh)
# ---------------------------------------------------------------------------

def test_counts_correct_after_bulk_upload(client, png_bytes):
    project = make_project(client, "BulkCounts")
    for i in range(5):
        upload_png(client, project["id"], f"img{i}.png", png_bytes)

    refreshed = client.get(f"/projects/{project['id']}").json()["data"]
    assert refreshed["images"] == 5
    assert refreshed["annotations"] == 0


def test_counts_correct_after_multi_file_single_request(client, png_bytes):
    project = make_project(client, "MultiFile")
    resp = client.post(
        f"/projects/{project['id']}/images",
        files=[
            ("files", ("a.png", png_bytes, "image/png")),
            ("files", ("b.png", png_bytes, "image/png")),
            ("files", ("c.png", png_bytes, "image/png")),
        ],
    )
    assert resp.status_code == 201
    assert len(resp.json()["data"]["uploaded"]) == 3

    refreshed = client.get(f"/projects/{project['id']}").json()["data"]
    assert refreshed["images"] == 3


# ---------------------------------------------------------------------------
# 5. API validation consistency
# ---------------------------------------------------------------------------

def test_validation_error_uses_envelope(client, png_bytes):
    project = make_project(client, "BadBody")
    image = upload_png(client, project["id"], "car.png", png_bytes)

    # width is not a number -> Pydantic request validation fails.
    resp = client.post(
        f"/projects/{project['id']}/images/{image['id']}/annotations",
        json={"x": 0.1, "y": 0.1, "width": "not-a-number", "height": 0.2},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert "error" in body and "data" not in body
    # Original FastAPI error list is preserved under error.detail.
    assert isinstance(body["error"]["detail"], list)
    assert body["error"]["detail"]


# ---------------------------------------------------------------------------
# 6. Path / ID validation
# ---------------------------------------------------------------------------

def test_is_safe_id_rejects_traversal_and_separators():
    from app.core import storage

    assert storage.is_safe_id("3f2504e0-4f89-41d3-9a0c-0305e82c3301") is True
    for bad in ("", "..", "../etc", "a/b", "a\\b", "..\\..\\win", "a\x00b"):
        assert storage.is_safe_id(bad) is False


def test_project_dir_raises_on_unsafe_id():
    import pytest

    from app.core import storage

    with pytest.raises(ValueError):
        storage.project_dir("../escape")


def test_managers_treat_unsafe_id_as_not_found(client):
    """Unsafe ids resolve to empty/None without raising or touching disk."""
    from app.services.annotation.manager import manager as annotation_manager
    from app.services.label.manager import manager as label_manager
    from app.services.project.manager import manager as project_manager
    from app.services.upload.manager import manager as upload_manager

    bad = "../../secret"
    assert project_manager.get_project(bad) is None
    assert project_manager.exists(bad) is False
    assert project_manager.delete_project(bad) is False
    assert label_manager.list_labels(bad) == []
    assert upload_manager.list_images(bad) == []
    assert annotation_manager.list_all(bad) == []


def test_api_rejects_unsafe_project_id(client):
    # A traversal-style id must not 500 or escape storage; it is simply absent.
    resp = client.get("/projects/..%2F..%2Fetc")
    assert resp.status_code == 404
