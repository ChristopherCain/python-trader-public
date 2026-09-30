import { useState } from "react";

const PALETTE = [
  "#ef4444", "#f97316", "#eab308", "#22c55e",
  "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899",
];

export default function LabelPanel({
  labels,
  activeLabelId,
  onSelect,
  onCreate,
  onDelete,
}) {
  const [name, setName] = useState("");
  const [color, setColor] = useState(PALETTE[0]);
  const [busy, setBusy] = useState(false);

  async function add(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      await onCreate(name.trim(), color);
      setName("");
      // Rotate to the next palette color for convenience.
      const idx = PALETTE.indexOf(color);
      setColor(PALETTE[(idx + 1) % PALETTE.length]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="section">
      <h3>Labels</h3>

      {labels.length === 0 ? (
        <div className="hint">No labels yet. Add one below, then draw a box.</div>
      ) : (
        labels.map((label) => (
          <div
            key={label.id}
            className={"label-item" + (label.id === activeLabelId ? " active" : "")}
            onClick={() => onSelect(label.id)}
          >
            <span className="label-swatch" style={{ background: label.color }} />
            <span className="name">{label.name}</span>
            <button
              className="del"
              title="Delete label"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(label);
              }}
            >
              ✕
            </button>
          </div>
        ))
      )}

      <form className="label-add" onSubmit={add}>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          title="Label color"
        />
        <input
          type="text"
          placeholder="New label"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="primary small" disabled={busy || !name.trim()}>
          Add
        </button>
      </form>
    </div>
  );
}
