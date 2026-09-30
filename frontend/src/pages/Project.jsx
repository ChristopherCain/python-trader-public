import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import Navbar from "../components/Navbar";
import UploadImage from "../components/UploadImage";
import ImageViewer from "../components/ImageViewer";
import LabelPanel from "../components/LabelPanel";
import ConfirmDialog from "../components/ConfirmDialog";
import ExpiryBadge from "../components/ExpiryBadge";

import { getProject } from "../api/projectApi";
import { getImages, deleteImage, imageFileUrl } from "../api/imageApi";
import { getLabels, createLabel, deleteLabel } from "../api/labelApi";
import {
  getAnnotations,
  createAnnotation,
  updateAnnotation,
  deleteAnnotation,
} from "../api/annotationApi";
import { downloadExport } from "../api/exportApi";

export default function Project() {
  const { id: projectId } = useParams();

  const [project, setProject] = useState(null);
  const [images, setImages] = useState([]);
  const [labels, setLabels] = useState([]);
  const [annotations, setAnnotations] = useState([]);

  const [selectedImageId, setSelectedImageId] = useState(null);
  const [activeLabelId, setActiveLabelId] = useState(null);
  const [selectedAnnId, setSelectedAnnId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [annLoading, setAnnLoading] = useState(false);
  const [toast, setToast] = useState(null);
  // The image awaiting delete confirmation (null = dialog closed).
  const [pendingDeleteImage, setPendingDeleteImage] = useState(null);
  // The export format currently being built/downloaded ("yolo" | "coco"), or
  // null when idle. Holding the format rather than a boolean lets only the
  // clicked button show its spinner while both stay disabled.
  const [exporting, setExporting] = useState(null);

  // ---- toast helper ----
  const notify = useCallback((message, kind = "ok") => {
    setToast({ message, kind });
    window.clearTimeout(notify._t);
    notify._t = window.setTimeout(() => setToast(null), 2600);
  }, []);

  // ---- initial load: project + images + labels ----
  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [proj, imgs, labs] = await Promise.all([
        getProject(projectId),
        getImages(projectId),
        getLabels(projectId),
      ]);
      setProject(proj);
      const imageList = Array.isArray(imgs) ? imgs : [];
      setImages(imageList);
      setLabels(Array.isArray(labs) ? labs : []);
      setSelectedImageId((cur) =>
        cur && imageList.some((i) => i.id === cur)
          ? cur
          : imageList[0]?.id || null
      );
      if (Array.isArray(labs) && labs.length > 0) {
        setActiveLabelId((cur) =>
          cur && labs.some((l) => l.id === cur) ? cur : labs[0].id
        );
      }
    } catch (err) {
      setError(err.message || "Failed to load project.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // ---- load annotations whenever the selected image changes ----
  useEffect(() => {
    if (!selectedImageId) {
      setAnnotations([]);
      return;
    }
    let cancelled = false;
    setAnnLoading(true);
    setSelectedAnnId(null);
    getAnnotations(projectId, selectedImageId)
      .then((data) => {
        if (!cancelled) setAnnotations(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!cancelled) notify(err.message || "Failed to load annotations.", "error");
      })
      .finally(() => {
        if (!cancelled) setAnnLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedImageId, notify]);

  const activeLabel = useMemo(
    () => labels.find((l) => l.id === activeLabelId) || null,
    [labels, activeLabelId]
  );

  const selectedIndex = useMemo(
    () => images.findIndex((i) => i.id === selectedImageId),
    [images, selectedImageId]
  );

  const labelName = useCallback(
    (labelId) => labels.find((l) => l.id === labelId)?.name || "unlabeled",
    [labels]
  );
  const labelColor = useCallback(
    (labelId) => labels.find((l) => l.id === labelId)?.color || "#9ca3af",
    [labels]
  );

  // ---- image handlers ----
  function handleUploaded(uploaded, skipped) {
    if (uploaded.length > 0) {
      setImages((prev) => [...prev, ...uploaded]);
      setSelectedImageId((cur) => cur || uploaded[0].id);
      notify(
        `Uploaded ${uploaded.length} image(s)` +
          (skipped ? `, skipped ${skipped}.` : ".")
      );
    } else {
      notify(skipped ? `Skipped ${skipped} file(s).` : "No images uploaded.", "error");
    }
  }

  async function handleDeleteImage(image) {
    // Opens the in-app confirmation; the delete itself runs in confirmDeleteImage.
    setPendingDeleteImage(image);
  }

  async function confirmDeleteImage() {
    const image = pendingDeleteImage;
    if (!image) return;
    try {
      await deleteImage(projectId, image.id);
      setImages((prev) => {
        const remaining = prev.filter((i) => i.id !== image.id);
        if (selectedImageId === image.id) {
          setSelectedImageId(remaining[0]?.id || null);
        }
        return remaining;
      });
      notify("Image deleted.");
    } catch (err) {
      notify(err.message || "Failed to delete image.", "error");
    } finally {
      setPendingDeleteImage(null);
    }
  }

  // ---- label handlers ----
  async function handleCreateLabel(name, color) {
    try {
      const label = await createLabel(projectId, name, color);
      setLabels((prev) => [...prev, label]);
      setActiveLabelId(label.id);
    } catch (err) {
      notify(err.message || "Failed to create label.", "error");
      throw err;
    }
  }

  async function handleDeleteLabel(label) {
    try {
      await deleteLabel(projectId, label.id);
      setLabels((prev) => prev.filter((l) => l.id !== label.id));
      if (activeLabelId === label.id) setActiveLabelId(null);
    } catch (err) {
      notify(err.message || "Failed to delete label.", "error");
    }
  }

  // ---- annotation handlers ----
  async function handleCreateAnnotation(box) {
    try {
      const payload = {
        label_id: activeLabel?.id || null,
        label: activeLabel?.name || "",
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      };
      const ann = await createAnnotation(projectId, selectedImageId, payload);
      setAnnotations((prev) => [...prev, ann]);
      setSelectedAnnId(ann.id);
    } catch (err) {
      notify(err.message || "Failed to create annotation.", "error");
    }
  }

  async function handleUpdateAnnotation(annId, box) {
    const existing = annotations.find((a) => a.id === annId);
    if (!existing) return;
    // Optimistic geometry update for a snappy canvas.
    setAnnotations((prev) =>
      prev.map((a) => (a.id === annId ? { ...a, ...box } : a))
    );
    try {
      const payload = {
        label_id: existing.label_id ?? null,
        label: existing.label ?? "",
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      };
      const updated = await updateAnnotation(projectId, selectedImageId, annId, payload);
      setAnnotations((prev) => prev.map((a) => (a.id === annId ? updated : a)));
    } catch (err) {
      notify(err.message || "Failed to update annotation.", "error");
      loadAnnotations();
    }
  }

  function loadAnnotations() {
    if (!selectedImageId) return;
    getAnnotations(projectId, selectedImageId)
      .then((data) => setAnnotations(Array.isArray(data) ? data : []))
      .catch(() => {});
  }

  // Reassign the selected annotation to the active label.
  async function relabelAnnotation(ann) {
    if (!activeLabel) {
      notify("Select a label first.", "error");
      return;
    }
    try {
      const payload = {
        label_id: activeLabel.id,
        label: activeLabel.name,
        x: ann.x,
        y: ann.y,
        width: ann.width,
        height: ann.height,
      };
      const updated = await updateAnnotation(projectId, selectedImageId, ann.id, payload);
      setAnnotations((prev) => prev.map((a) => (a.id === ann.id ? updated : a)));
    } catch (err) {
      notify(err.message || "Failed to relabel.", "error");
    }
  }

  async function handleDeleteAnnotation(ann) {
    try {
      await deleteAnnotation(projectId, selectedImageId, ann.id);
      setAnnotations((prev) => prev.filter((a) => a.id !== ann.id));
      if (selectedAnnId === ann.id) setSelectedAnnId(null);
    } catch (err) {
      notify(err.message || "Failed to delete annotation.", "error");
    }
  }

  // ---- export ----
  async function handleExport(format) {
    if (exporting) return; // building an archive twice at once helps nobody
    if (images.length === 0) {
      notify("Add images before exporting.", "error");
      return;
    }
    const upper = format.toUpperCase();
    setExporting(format);
    notify(`Building ${upper} export…`);
    try {
      await downloadExport(projectId, format, project?.name || "dataset");
      notify("Export ready — check your downloads.");
    } catch (err) {
      notify(err.message || "Failed to export dataset.", "error");
    } finally {
      setExporting(null);
    }
  }

  // ---- keyboard: Delete removes selected box, arrows switch images ----
  useEffect(() => {
    function onKey(e) {
      const tag = e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if ((e.key === "Delete" || e.key === "Backspace") && selectedAnnId) {
        const ann = annotations.find((a) => a.id === selectedAnnId);
        if (ann) {
          e.preventDefault();
          handleDeleteAnnotation(ann);
        }
      } else if (e.key === "ArrowLeft" && selectedIndex > 0) {
        setSelectedImageId(images[selectedIndex - 1].id);
      } else if (e.key === "ArrowRight" && selectedIndex < images.length - 1) {
        setSelectedImageId(images[selectedIndex + 1].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedAnnId, annotations, selectedIndex, images]);

  const crumb = project ? project.name || "Untitled Project" : "…";

  // ---- render ----
  if (loading) {
    return (
      <>
        <Navbar crumb="Loading…" />
        <div className="state">
          <span className="spin" /> Loading workspace…
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Navbar />
        <div className="state error">
          {error}
          <div style={{ marginTop: 12 }}>
            <button onClick={loadWorkspace}>Retry</button>
          </div>
        </div>
      </>
    );
  }

  const currentImage = images[selectedIndex] || null;

  return (
    <>
      <Navbar
        crumb={crumb}
        right={
          <>
            {/* Renders nothing unless the server gave this project a deadline. */}
            <ExpiryBadge
              seconds={project?.seconds_remaining}
              onExpire={loadWorkspace}
            />
            <button
              className="primary"
              onClick={() => handleExport("yolo")}
              disabled={!!exporting}
              title="Download this project as a YOLO dataset (ZIP)"
            >
              {exporting === "yolo" ? (
                <>
                  <span className="spin" /> Exporting…
                </>
              ) : (
                "Export YOLO"
              )}
            </button>
            <button
              className="primary"
              onClick={() => handleExport("coco")}
              disabled={!!exporting}
              title="Download this project as a COCO dataset (ZIP)"
            >
              {exporting === "coco" ? (
                <>
                  <span className="spin" /> Exporting…
                </>
              ) : (
                "Export COCO"
              )}
            </button>
          </>
        }
      />

      <div className="workspace">
        {/* Left: upload + image list */}
        <aside className="panel left">
          <UploadImage
            projectId={projectId}
            onUploaded={handleUploaded}
            onError={(m) => notify(m, "error")}
          />

          <div className="section">
            <h3>Images ({images.length})</h3>
            {images.length === 0 ? (
              <div className="hint">No images yet. Upload some to begin.</div>
            ) : (
              images.map((img) => (
                <div
                  key={img.id}
                  className={"thumb" + (img.id === selectedImageId ? " active" : "")}
                  onClick={() => setSelectedImageId(img.id)}
                >
                  <img
                    src={imageFileUrl(projectId, img.id)}
                    alt={img.original_filename || img.filename}
                    loading="lazy"
                  />
                  <span className="name">
                    {img.original_filename || img.filename}
                  </span>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Center: toolbar + canvas */}
        <main className="canvas-wrap">
          <div className="canvas-toolbar">
            <button
              className="small"
              disabled={selectedIndex <= 0}
              onClick={() => setSelectedImageId(images[selectedIndex - 1].id)}
            >
              ← Prev
            </button>
            <button
              className="small"
              disabled={selectedIndex < 0 || selectedIndex >= images.length - 1}
              onClick={() => setSelectedImageId(images[selectedIndex + 1].id)}
            >
              Next →
            </button>
            <span className="muted">
              {currentImage
                ? `${selectedIndex + 1} / ${images.length} · ${
                    currentImage.original_filename || currentImage.filename
                  }`
                : "No image selected"}
            </span>
            <span style={{ flex: 1 }} />
            {currentImage ? (
              <button
                className="danger small"
                onClick={() => handleDeleteImage(currentImage)}
              >
                Delete image
              </button>
            ) : null}
          </div>

          <ImageViewer
            imageUrl={currentImage ? imageFileUrl(projectId, currentImage.id) : null}
            annotations={annotations}
            labels={labels}
            activeLabel={activeLabel}
            selectedId={selectedAnnId}
            onSelect={setSelectedAnnId}
            onCreate={handleCreateAnnotation}
            onUpdate={handleUpdateAnnotation}
          />
        </main>

        {/* Right: labels + annotations */}
        <aside className="panel right">
          <LabelPanel
            labels={labels}
            activeLabelId={activeLabelId}
            onSelect={setActiveLabelId}
            onCreate={handleCreateLabel}
            onDelete={handleDeleteLabel}
          />

          <div className="section">
            <h3>Annotations ({annotations.length})</h3>
            {!currentImage ? (
              <div className="hint">Select an image to see its boxes.</div>
            ) : annLoading ? (
              <div className="hint">
                <span className="spin" /> Loading…
              </div>
            ) : annotations.length === 0 ? (
              <div className="hint">
                Draw a box on the image to add your first annotation.
              </div>
            ) : (
              annotations.map((ann) => (
                <div
                  key={ann.id}
                  className={"ann-item" + (ann.id === selectedAnnId ? " active" : "")}
                  onClick={() => setSelectedAnnId(ann.id)}
                  onDoubleClick={() => relabelAnnotation(ann)}
                  title="Double-click to reassign to the active label"
                >
                  <span
                    className="label-swatch"
                    style={{ background: labelColor(ann.label_id) }}
                  />
                  <span className="name">{ann.label || labelName(ann.label_id)}</span>
                  <button
                    className="del"
                    title="Delete annotation"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteAnnotation(ann);
                    }}
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>

      {pendingDeleteImage ? (
        <ConfirmDialog
          title="Delete image"
          message="This will permanently remove"
          highlight={`“${
            pendingDeleteImage.original_filename || pendingDeleteImage.filename
          }”`}
          note="and every bounding box drawn on it. This cannot be undone."
          confirmText="Delete image"
          onConfirm={confirmDeleteImage}
          onCancel={() => setPendingDeleteImage(null)}
        />
      ) : null}

      {toast ? <div className={"toast " + toast.kind}>{toast.message}</div> : null}
    </>
  );
}
