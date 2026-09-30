"""Regression test: YOLO export golden output.

This is the most valuable safety net in the suite: it pins the exact bytes of
the exported YOLO dataset so any change to the export math or archive layout is
caught immediately.

Golden math (top-left normalized box -> YOLO center format):
    box   = {x: 0.1, y: 0.2, width: 0.4, height: 0.3}
    cx    = x + width/2  = 0.1 + 0.20 = 0.30
    cy    = y + height/2 = 0.2 + 0.15 = 0.35
    line  = "0 0.300000 0.350000 0.400000 0.300000"   (class 0 = "car")
    classes.txt = "car\n"

Archive layout (arcnames relative to the export root):
    dataset/classes.txt
    dataset/data.yaml
    dataset/train.txt
    dataset/val.txt
    dataset/images/<stored image filename>
    dataset/labels/<image stem>.txt
"""

import io
import zipfile

from conftest import make_annotation, make_label, make_project, upload_png

BOX = {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}


def _open_export_zip(client, project_id):
    resp = client.get(f"/projects/{project_id}/export/yolo")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(resp.content))


def _read_text(zf, name):
    """Read a text member and normalize newlines to LF.

    The export writes files with Python text-mode ``write_text``, so on Windows
    each ``\\n`` becomes ``\\r\\n``. Normalizing CRLF -> LF here makes the golden
    assertions newline-independent while still verifying exact class ordering
    and content byte-for-byte otherwise.
    """
    return zf.read(name).decode("utf-8").replace("\r\n", "\n")


def test_yolo_export_golden_output(client, png_bytes):
    project = make_project(client, "Golden")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    make_annotation(client, project["id"], image["id"], BOX, label=car)

    stem = image["filename"].rsplit(".", 1)[0]  # stored filename stem

    with _open_export_zip(client, project["id"]) as zf:
        names = set(zf.namelist())
        assert "dataset/classes.txt" in names
        assert f"dataset/images/{image['filename']}" in names
        assert f"dataset/labels/{stem}.txt" in names

        # classes.txt: one class name per line, newline-terminated.
        classes = _read_text(zf, "dataset/classes.txt")
        assert classes == "car\n"

        # The label file holds the exact center-format line for class 0.
        label_txt = _read_text(zf, f"dataset/labels/{stem}.txt")
        assert label_txt == "0 0.300000 0.350000 0.400000 0.300000\n"


def test_yolo_export_multiple_labels_indexed_by_order(client, png_bytes):
    project = make_project(client, "MultiLabel")
    image = upload_png(client, project["id"], "scene.png", png_bytes)
    # Label order defines the class index: car=0, person=1.
    car = make_label(client, project["id"], "car")
    person = make_label(client, project["id"], "person")

    make_annotation(
        client, project["id"], image["id"],
        {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}, label=car,
    )
    make_annotation(
        client, project["id"], image["id"],
        {"x": 0.5, "y": 0.5, "width": 0.4, "height": 0.4}, label=person,
    )

    stem = image["filename"].rsplit(".", 1)[0]

    with _open_export_zip(client, project["id"]) as zf:
        classes = _read_text(zf, "dataset/classes.txt")
        assert classes == "car\nperson\n"

        lines = _read_text(zf, f"dataset/labels/{stem}.txt").splitlines()
        # car box: cx=0.25, cy=0.25, w=0.5, h=0.5  -> class 0
        # person box: cx=0.70, cy=0.70, w=0.4, h=0.4 -> class 1
        assert lines[0] == "0 0.250000 0.250000 0.500000 0.500000"
        assert lines[1] == "1 0.700000 0.700000 0.400000 0.400000"


def test_yolo_export_skips_box_with_deleted_label(client, png_bytes):
    """Current behavior: a box whose label_id is not in labels.json is skipped.

    This documents the *existing* orphan-handling in export (M1 will revisit
    whether label deletion should be blocked). Here we simulate an orphan by
    giving the annotation a label_id that no label owns.
    """
    project = make_project(client, "Orphan")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    make_label(client, project["id"], "car")

    # Annotation references a non-existent label id -> not in class_index.
    client.post(
        f"/projects/{project['id']}/images/{image['id']}/annotations",
        json={**BOX, "label_id": "ghost-label", "label": "ghost"},
    )

    stem = image["filename"].rsplit(".", 1)[0]
    with _open_export_zip(client, project["id"]) as zf:
        label_txt = _read_text(zf, f"dataset/labels/{stem}.txt")
        # The orphan box is skipped -> empty label file.
        assert label_txt == ""


def test_yolo_export_unknown_project_returns_404(client):
    assert client.get("/projects/nope/export/yolo").status_code == 404


# ---------------------------------------------------------------------------
# data.yaml + train/val split
# ---------------------------------------------------------------------------

def _parse_data_yaml(zf):
    """Parse the subset of YAML that data.yaml uses.

    Deliberately hand-rolled: the backend writes the file as plain text and has
    no YAML dependency, so the test should not add one either. Handles top-level
    ``key: value`` pairs plus the indented ``names:`` mapping.
    """
    text = _read_text(zf, "dataset/data.yaml")
    flat, names = {}, {}
    in_names = False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" "):
            if in_names and ":" in raw:
                key, _, value = raw.strip().partition(":")
                names[int(key)] = value.strip().strip('"')
            continue
        in_names = False
        key, _, value = raw.partition(":")
        if key == "names":
            in_names = True
            continue
        flat[key.strip()] = value.strip()
    return flat, names


def _manifest(zf, name):
    """Read train.txt / val.txt into a list of image paths."""
    return [
        line for line in _read_text(zf, f"dataset/{name}").splitlines() if line.strip()
    ]


def test_data_yaml_has_required_keys_and_class_mapping(client, png_bytes):
    project = make_project(client, "Yaml")
    image = upload_png(client, project["id"], "car.png", png_bytes)
    car = make_label(client, project["id"], "car")
    make_label(client, project["id"], "person")
    make_annotation(client, project["id"], image["id"], BOX, label=car)

    with _open_export_zip(client, project["id"]) as zf:
        assert "dataset/data.yaml" in set(zf.namelist())
        flat, names = _parse_data_yaml(zf)

        # The four required keys, plus nc for trainers that still want it.
        assert flat["path"] == "."
        assert flat["train"] == "train.txt"
        assert flat["val"] == "val.txt"
        assert flat["nc"] == "2"

        # Class mapping mirrors label order, matching classes.txt indices.
        assert names == {0: "car", 1: "person"}


def test_data_yaml_quotes_awkward_label_names(client, png_bytes):
    """A label containing YAML syntax must not corrupt data.yaml."""
    project = make_project(client, "Quoting")
    upload_png(client, project["id"], "car.png", png_bytes)
    make_label(client, project["id"], 'road: "sign"')

    with _open_export_zip(client, project["id"]) as zf:
        raw = _read_text(zf, "dataset/data.yaml")
        # The inner quotes are escaped, so the scalar stays terminated.
        assert '0: "road: \\"sign\\""' in raw


def test_split_is_80_20_and_deterministic(client, png_bytes):
    """10 images -> 8 train / 2 val, and re-exporting gives the same split."""
    project = make_project(client, "Split")
    pid = project["id"]
    for i in range(10):
        upload_png(client, pid, f"img{i}.png", png_bytes)

    with _open_export_zip(client, pid) as zf:
        train, val = _manifest(zf, "train.txt"), _manifest(zf, "val.txt")

    assert len(train) == 8
    assert len(val) == 2
    # No image is in both sets, and together they cover every image.
    assert set(train).isdisjoint(val)
    assert len(set(train) | set(val)) == 10

    # Same project exported again -> identical manifests (no RNG, no clock).
    with _open_export_zip(client, pid) as zf:
        assert _manifest(zf, "train.txt") == train
        assert _manifest(zf, "val.txt") == val


def test_manifest_entries_resolve_to_real_archive_members(client, png_bytes):
    """Every listed path must exist in the ZIP, with a paired label file."""
    project = make_project(client, "Manifest")
    pid = project["id"]
    for i in range(6):
        upload_png(client, pid, f"shot{i}.png", png_bytes)

    with _open_export_zip(client, pid) as zf:
        members = set(zf.namelist())
        listed = _manifest(zf, "train.txt") + _manifest(zf, "val.txt")
        assert listed, "split manifests must not both be empty"
        for entry in listed:
            assert entry.startswith("./images/"), entry
            name = entry[len("./images/") :]
            assert f"dataset/images/{name}" in members, entry
            # Label discovery works by swapping images/ for labels/.
            stem = name.rsplit(".", 1)[0]
            assert f"dataset/labels/{stem}.txt" in members, entry


def test_small_dataset_still_gets_a_validation_set(client, png_bytes):
    """Under 5 images the stride selects nothing, so val must be backfilled."""
    for count in (2, 3, 4):
        project = make_project(client, f"Small{count}")
        pid = project["id"]
        for i in range(count):
            upload_png(client, pid, f"a{i}.png", png_bytes)

        with _open_export_zip(client, pid) as zf:
            train, val = _manifest(zf, "train.txt"), _manifest(zf, "val.txt")

        assert len(val) == 1, (count, val)
        assert len(train) == count - 1, (count, train)
        assert set(train).isdisjoint(val)


def test_single_image_appears_in_both_splits(client, png_bytes):
    """One image cannot be split, so it is reused rather than left in one set."""
    project = make_project(client, "Single")
    upload_png(client, project["id"], "only.png", png_bytes)

    with _open_export_zip(client, project["id"]) as zf:
        assert _manifest(zf, "train.txt") == ["./images/only.png"]
        assert _manifest(zf, "val.txt") == ["./images/only.png"]


def test_unannotated_images_still_export_with_empty_label_files(client, png_bytes):
    """An image with no boxes gets an empty .txt and still joins the split."""
    project = make_project(client, "NoBoxes")
    pid = project["id"]
    labelled = upload_png(client, pid, "has.png", png_bytes)
    upload_png(client, pid, "none.png", png_bytes)
    car = make_label(client, pid, "car")
    make_annotation(client, pid, labelled["id"], BOX, label=car)

    with _open_export_zip(client, pid) as zf:
        members = set(zf.namelist())
        assert "dataset/labels/none.txt" in members
        assert _read_text(zf, "dataset/labels/none.txt") == ""
        assert _read_text(zf, "dataset/labels/has.txt") == (
            "0 0.300000 0.350000 0.400000 0.300000\n"
        )
        # Both images are still described by the split.
        listed = _manifest(zf, "train.txt") + _manifest(zf, "val.txt")
        assert "./images/none.png" in listed
        assert "./images/has.png" in listed


def test_project_with_no_labels_still_yields_valid_data_yaml(client, png_bytes):
    """A project labelled by nobody yet must not emit broken YAML."""
    project = make_project(client, "Unlabelled")
    upload_png(client, project["id"], "car.png", png_bytes)

    with _open_export_zip(client, project["id"]) as zf:
        flat, names = _parse_data_yaml(zf)
        assert flat["nc"] == "0"
        assert names == {}
        assert "names:\n  {}" in _read_text(zf, "dataset/data.yaml")


def test_all_yolo_coordinates_are_normalized(client, png_bytes):
    """Every exported number must sit inside 0..1."""
    project = make_project(client, "Normalized")
    pid = project["id"]
    image = upload_png(client, pid, "car.png", png_bytes)
    car = make_label(client, pid, "car")
    for box in (
        {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        {"x": 0.7, "y": 0.8, "width": 0.25, "height": 0.15},
    ):
        make_annotation(client, pid, image["id"], box, label=car)

    with _open_export_zip(client, pid) as zf:
        lines = _read_text(zf, "dataset/labels/car.txt").splitlines()

    assert len(lines) == 2
    for line in lines:
        parts = line.split()
        assert parts[0] == "0"  # class id is an integer index
        for value in parts[1:]:
            assert 0.0 <= float(value) <= 1.0, line
