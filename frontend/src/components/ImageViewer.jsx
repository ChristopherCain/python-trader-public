import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Bounding-box editor: an <img> visual layer with a TRANSPARENT <canvas>
 * overlay on top that owns all drawing/interaction.
 *
 * The photo is shown by a non-interactive <img> (pointer-events:none,
 * draggable=false) so the browser can never drag a ghost copy of it. The
 * overlay canvas receives pointer events and paints only the boxes.
 *
 * Boxes are stored in NORMALIZED coordinates (0..1) so they stay correct at
 * any display size. The overlay is sized to the image's aspect ratio, scaled
 * to fit the stage, and re-fits on window resize.
 *
 * Props:
 *   imageUrl, annotations[], labels[], activeLabel, selectedId
 *   onSelect(id), onCreate(box), onUpdate(id, box)
 */

const HANDLE = 8; // px hit radius for resize handles
const MIN_SIZE = 0.01; // minimum normalized box size

export default function ImageViewer({
  imageUrl,
  annotations = [],
  labels = [],
  activeLabel,
  selectedId,
  onSelect,
  onCreate,
  onUpdate,
}) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const imgRef = useRef(null);
  const imgElRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [size, setSize] = useState({ w: 0, h: 0 });

  // Active interaction (draw/move/resize). Kept in a ref + a state bump so
  // the draw effect re-runs without stale closures.
  const drag = useRef(null);
  const [, bump] = useState(0);
  const redraw = () => bump((n) => n + 1);

  const labelColor = useCallback(
    (labelId) => labels.find((l) => l.id === labelId)?.color || "#7c3aed",
    [labels]
  );

  // Load image whenever the URL changes.
  useEffect(() => {
    setImgLoaded(false);
    if (!imageUrl) return;
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      setImgLoaded(true);
    };
    img.onerror = () => {
      imgRef.current = null;
      setImgLoaded(false);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Fit the canvas to its container, preserving aspect ratio.
  const fit = useCallback(() => {
    const img = imgRef.current;
    const wrap = wrapRef.current;
    if (!img || !wrap) return;
    const maxW = wrap.clientWidth - 4;
    const maxH = wrap.clientHeight - 4;
    const scale = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1);
    setSize({
      w: Math.max(1, Math.round(img.naturalWidth * scale)),
      h: Math.max(1, Math.round(img.naturalHeight * scale)),
    });
  }, []);

  useEffect(() => {
    if (!imgLoaded) return;
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [imgLoaded, fit]);

  // Belt-and-braces: kill the browser's native drag on the <img> layer with a
  // NATIVE dragstart listener. The <img> is also pointer-events:none +
  // draggable=false via CSS/attr, so it can't be a drag source or intercept
  // the overlay — this just guarantees no ghost even if a browser ignores the
  // attribute. preventDefault() on a React handler alone does NOT stop DnD.
  useEffect(() => {
    const el = imgElRef.current;
    if (!el || !imgLoaded) return;
    const prevent = (e) => e.preventDefault();
    el.addEventListener("dragstart", prevent);
    return () => el.removeEventListener("dragstart", prevent);
  }, [imgLoaded]);

  // Paint the boxes onto the TRANSPARENT overlay canvas. The photo itself is
  // rendered by the <img> layer underneath, so we only draw annotations here.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { w, h } = size;
    if (w === 0 || h === 0) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);

    const live = drag.current && drag.current.live;

    for (const a of annotations) {
      const box = live && drag.current.id === a.id ? { ...a, ...live } : a;
      const x = box.x * w;
      const y = box.y * h;
      const bw = box.width * w;
      const bh = box.height * h;
      const color = labelColor(box.label_id);
      const selected = a.id === selectedId;

      ctx.lineWidth = selected ? 3 : 2;
      ctx.strokeStyle = color;
      ctx.strokeRect(x, y, bw, bh);

      const text = box.label || "unlabeled";
      ctx.font = "12px system-ui, sans-serif";
      const tw = ctx.measureText(text).width + 8;
      ctx.fillStyle = color;
      ctx.fillRect(x, Math.max(0, y - 16), tw, 16);
      ctx.fillStyle = "#fff";
      ctx.fillText(text, x + 4, Math.max(11, y - 4));

      if (selected) {
        ctx.fillStyle = "#fff";
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        for (const [hx, hy] of corners(x, y, bw, bh)) {
          ctx.beginPath();
          ctx.rect(hx - HANDLE / 2, hy - HANDLE / 2, HANDLE, HANDLE);
          ctx.fill();
          ctx.stroke();
        }
      }
    }

    // In-progress new box.
    if (drag.current && drag.current.mode === "create" && drag.current.current) {
      const b = boxFromPoints(drag.current.start, drag.current.current);
      ctx.setLineDash([5, 4]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = activeLabel ? activeLabel.color : "#7c3aed";
      ctx.strokeRect(b.x * w, b.y * h, b.width * w, b.height * h);
      ctx.setLineDash([]);
    }
  }, [annotations, size, selectedId, activeLabel, labelColor]);

  function toNorm(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: clamp01((e.clientX - rect.left) / rect.width),
      y: clamp01((e.clientY - rect.top) / rect.height),
    };
  }

  function hitHandle(a, pt) {
    const { w, h } = size;
    const px = pt.x * w;
    const py = pt.y * h;
    const names = ["nw", "ne", "se", "sw"];
    const cs = corners(a.x * w, a.y * h, a.width * w, a.height * h);
    for (let i = 0; i < cs.length; i++) {
      if (Math.abs(px - cs[i][0]) <= HANDLE && Math.abs(py - cs[i][1]) <= HANDLE) {
        return names[i];
      }
    }
    return null;
  }

  function insideBox(a, pt) {
    return (
      pt.x >= a.x &&
      pt.x <= a.x + a.width &&
      pt.y >= a.y &&
      pt.y <= a.y + a.height
    );
  }

  function onPointerDown(e) {
    if (!imgLoaded) return;
    // Only react to the primary (left) button; ignore right/middle clicks.
    if (e.button !== 0) return;
    // Stop the browser from starting a native image-drag / text selection,
    // which would otherwise hijack the drag and prevent box drawing.
    e.preventDefault();
    // Capture the pointer so move/up keep firing even if the cursor leaves
    // the canvas mid-drag (e.g. drawing a box out to the very edge).
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // setPointerCapture can throw if the pointer is already gone; ignore.
    }
    const pt = toNorm(e);

    const selected = annotations.find((a) => a.id === selectedId);
    if (selected) {
      const handle = hitHandle(selected, pt);
      if (handle) {
        drag.current = {
          mode: "resize",
          handle,
          id: selected.id,
          box: { ...selected },
          pointerId: e.pointerId,
        };
        return;
      }
    }

    for (let i = annotations.length - 1; i >= 0; i--) {
      if (insideBox(annotations[i], pt)) {
        onSelect && onSelect(annotations[i].id);
        drag.current = {
          mode: "move",
          id: annotations[i].id,
          box: { ...annotations[i] },
          start: pt,
          pointerId: e.pointerId,
        };
        return;
      }
    }

    onSelect && onSelect(null);
    drag.current = { mode: "create", start: pt, current: pt, pointerId: e.pointerId };
    redraw();
  }

  function onPointerCancel() {
    // A native gesture or the OS cancelled the pointer stream. Abort any
    // in-progress draw instead of committing a stray/zero-size box.
    drag.current = null;
    redraw();
  }

  function onPointerMove(e) {
    if (!drag.current) return;
    e.preventDefault();
    const pt = toNorm(e);
    const d = drag.current;

    if (d.mode === "create") {
      d.current = pt;
    } else if (d.mode === "move") {
      const dx = pt.x - d.start.x;
      const dy = pt.y - d.start.y;
      const nx = Math.min(clamp01(d.box.x + dx), 1 - d.box.width);
      const ny = Math.min(clamp01(d.box.y + dy), 1 - d.box.height);
      d.live = { x: nx, y: ny, width: d.box.width, height: d.box.height };
    } else if (d.mode === "resize") {
      d.live = resizeBox(d.box, d.handle, pt);
    }
    redraw();
  }

  function onPointerUp(e) {
    const d = drag.current;
    if (d && e) {
      try {
        e.currentTarget.releasePointerCapture(d.pointerId);
      } catch {
        // Already released / pointer gone; nothing to do.
      }
    }
    drag.current = null;
    if (!d) {
      redraw();
      return;
    }

    if (d.mode === "create") {
      const box = boxFromPoints(d.start, d.current);
      // Ignore accidental clicks / tiny drags below the minimum box size.
      if (box.width >= MIN_SIZE && box.height >= MIN_SIZE) {
        onCreate && onCreate(box);
      }
    } else if ((d.mode === "move" || d.mode === "resize") && d.live) {
      if (d.live.width >= MIN_SIZE && d.live.height >= MIN_SIZE) {
        onUpdate && onUpdate(d.id, d.live);
      }
    }
    redraw();
  }

  if (!imageUrl) {
    return (
      <div className="canvas-stage">
        <div className="placeholder">Select an image to start labeling.</div>
      </div>
    );
  }

  return (
    <div className="canvas-stage" ref={wrapRef}>
      {!imgLoaded ? (
        <div className="placeholder">
          <span className="spin" /> Loading image…
        </div>
      ) : (
        <div
          className="bbox-frame"
          style={{ width: size.w, height: size.h }}
        >
          {/* Visual layer: the photo. Non-interactive and non-draggable so
              the browser can never start a native image-drag ghost. */}
          <img
            ref={imgElRef}
            className="bbox-image"
            src={imageUrl}
            alt=""
            draggable={false}
          />
          {/* Interaction layer: transparent overlay that owns all drawing
              events and shows the crosshair cursor. */}
          <canvas
            ref={canvasRef}
            className="bbox-canvas"
            width={size.w}
            height={size.h}
            draggable={false}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerCancel}
          />
        </div>
      )}
    </div>
  );
}

// ---- pure helpers ----
function clamp01(v) {
  return Math.max(0, Math.min(1, v));
}

function corners(x, y, w, h) {
  return [
    [x, y],
    [x + w, y],
    [x + w, y + h],
    [x, y + h],
  ];
}

function boxFromPoints(a, b) {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(a.x - b.x),
    height: Math.abs(a.y - b.y),
  };
}

function resizeBox(box, handle, pt) {
  let left = box.x;
  let top = box.y;
  let right = box.x + box.width;
  let bottom = box.y + box.height;

  if (handle.includes("w")) left = clamp01(pt.x);
  if (handle.includes("e")) right = clamp01(pt.x);
  if (handle.includes("n")) top = clamp01(pt.y);
  if (handle.includes("s")) bottom = clamp01(pt.y);

  return {
    x: Math.min(left, right),
    y: Math.min(top, bottom),
    width: Math.abs(right - left),
    height: Math.abs(bottom - top),
  };
}
