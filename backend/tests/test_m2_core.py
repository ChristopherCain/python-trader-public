"""Regression tests for M2 — Core V1 implementation.

M2 hardens the core labeling pipeline's reliability without changing the
existing workflow. Two genuinely new guarantees are locked here:

  1. Annotation update/delete respect the image named in the request path.
     Matching on annotation id alone let a call against the wrong image URL
     mutate or delete an unrelated annotation; that cross-reference is now a
     404.
  2. YOLO export never loses a label file to a stem collision. Two images that
     share a stem (e.g. ``cat.jpg`` and ``cat.png``) previously mapped to the
     same ``cat.txt`` and one silently overwrote the other. Each image now gets
     a paired, unique image/label stem so no annotations vanish.

These are additive: the M0/M1 suites still pin every prior contract, including
the orphan-label tolerance M1 introduced (which M2 intentionally preserves).
"""

import io
import zipfile

from conftest import make_annotation, make_label, make_project, upload_png

BOX = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}


def _export_zip(client, project_id):
    resp = client.get(f"/projects/{project_id}/export/yolo")
    assert resp.status_code == 200, resp.text
    return zipfile.ZipFile(io.BytesIO(resp.content))


# ---------------------------------------------------------------------------
# M2.1 — annotation update/delete honor the image in the request path
# ---------------------------------------------------------------------------

def test_update_annotation_wrong_image_is_not_found(client, png_bytes):
    """PUT under the wrong image URL must not mutate the annotation."""
    project = make_project(client)
    pid = project["id"]
    img_a = upload_png(client, pid, "a.png", png_bytes)
    img_b = upload_png(client, pid, "b.png", png_bytes)
    label = make_label(client, pid, "car")

    ann = make_annotation(client, pid, img_a["id"], BOX, label=label)

    # Same annotation id, but addressed through image B's URL.
    resp = client.put(
        f"/projects/{pid}/images/{img_b['id']}/annotations/{ann['id']}",
        json={
            "label_id": label["id"],
            "label": label["name"],
            "x": 0.5,
            "y": 0.5,
            "width": 0.2,
            "height": 0.2,
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["success"] is False

    # The stored annotation is untouched: still under image A, original box.
    listed = client.get(f"/projects/{pid}/images/{img_a['id']}/annotations")
    boxes = listed.json()["data"]
    assert len(boxes) == 1
    assert boxes[0]["x"] == BOX["x"]
    assert boxes[0]["width"] == BOX["width"]


def test_delete_annotation_wrong_image_is_not_found(client, png_bytes):
    """DELETE under the wrong image URL must not remove the annotation."""
    project = make_project(client)
    pid = project["id"]
    img_a = upload_png(client, pid, "a.png", png_bytes)
    img_b = upload_png(client, pid, "b.png", png_bytes)
    label = make_label(client, pid, "car")

    ann = make_annotation(client, pid, img_a["id"], BOX, label=label)

    resp = client.delete(
        f"/projects/{pid}/images/{img_b['id']}/annotations/{ann['id']}"
    )
    assert resp.status_code == 404, resp.text

    # Annotation still present under its real image.
    listed = client.get(f"/projects/{pid}/images/{img_a['id']}/annotations")
    assert len(listed.json()["data"]) == 1


def test_update_delete_with_correct_image_still_work(client, png_bytes):
    """The guard is transparent to a correctly-addressed request."""
    project = make_project(client)
    pid = project["id"]
    image = upload_png(client, pid, "a.png", png_bytes)
    label = make_label(client, pid, "car")

    ann = make_annotation(client, pid, image["id"], BOX, label=label)

    upd = client.put(
        f"/projects/{pid}/images/{image['id']}/annotations/{ann['id']}",
        json={
            "label_id": label["id"],
            "label": label["name"],
            "x": 0.5,
            "y": 0.5,
            "width": 0.2,
            "height": 0.2,
        },
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["data"]["x"] == 0.5

    dele = client.delete(
        f"/projects/{pid}/images/{image['id']}/annotations/{ann['id']}"
    )
    assert dele.status_code == 200, dele.text

    listed = client.get(f"/projects/{pid}/images/{image['id']}/annotations")
    assert listed.json()["data"] == []


# ---------------------------------------------------------------------------
# M2.2 — YOLO export never loses a label file to a stem collision
# ---------------------------------------------------------------------------

def test_export_colliding_stems_keep_both_label_files(client, png_bytes):
    """cat.jpg and cat.png must each keep their own label file + box."""
    project = make_project(client)
    pid = project["id"]
    img_jpg = upload_png(client, pid, "cat.jpg", png_bytes)
    img_png = upload_png(client, pid, "cat.png", png_bytes)
    label = make_label(client, pid, "cat")

    # Two visibly different boxes so we can tell the label files apart.
    make_annotation(
        client, pid, img_jpg["id"],
        {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}, label=label,
    )
    make_annotation(
        client, pid, img_png["id"],
        {"x": 0.6, "y": 0.6, "width": 0.3, "height": 0.3}, label=label,
    )

    zf = _export_zip(client, pid)
    label_files = sorted(
        n for n in zf.namelist()
        if n.startswith("dataset/labels/") and n.endswith(".txt")
    )
    # Two distinct label files (not one overwritten), both non-empty.
    assert len(label_files) == 2, label_files
    contents = [zf.read(name).decode("utf-8").strip() for name in label_files]
    assert all(contents), contents
    # Both boxes survived: their distinct center-x values are both present.
    joined = "\n".join(contents)
    assert "0.200000" in joined  # cx of the jpg box (0.1 + 0.2/2)
    assert "0.750000" in joined  # cx of the png box (0.6 + 0.3/2)

    # And each label file is paired with a copied image of the same stem.
    image_files = sorted(
        n for n in zf.namelist() if n.startswith("dataset/images/")
    )
    assert len(image_files) == 2, image_files
    label_stems = {n.rsplit("/", 1)[1][:-4] for n in label_files}
    image_stems = {n.rsplit("/", 1)[1].rsplit(".", 1)[0] for n in image_files}
    assert label_stems == image_stems


def test_export_distinct_stems_use_plain_names(client, png_bytes):
    """Non-colliding stems are exported verbatim (no disambiguation suffix)."""
    project = make_project(client)
    pid = project["id"]
    img = upload_png(client, pid, "dog.png", png_bytes)
    label = make_label(client, pid, "dog")
    make_annotation(client, pid, img["id"], BOX, label=label)

    zf = _export_zip(client, pid)
    names = zf.namelist()
    assert "dataset/labels/dog.txt" in names
    assert "dataset/images/dog.png" in names
