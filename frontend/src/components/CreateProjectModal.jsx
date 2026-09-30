import { useEffect, useState } from "react";

import { formatHours, formatHoursCompound } from "../utils/expiry";

/**
 * New-project dialog.
 *
 * On the public deployment every project is temporary, so the dialog carries an
 * inline notice stating exactly what will happen and when. It lives inside the
 * create flow rather than as a second confirmation step: the warning is
 * unmissable before the primary action, without adding a click for a user who
 * has already read it. Self-hosted mode passes `temporary={false}` and the
 * dialog looks exactly as it did in v1.0.0.
 *
 * Props:
 *   temporary  whether the backend expires projects (from GET /config)
 *   ttlHours   project lifetime in hours, as reported by the backend
 */
export default function CreateProjectModal({
  onClose,
  onCreate,
  temporary = false,
  ttlHours = null,
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Close on Escape.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCreate(name.trim() || "Untitled Project");
      onClose();
    } catch (err) {
      setError(err.message || "Failed to create project.");
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <form
        className="modal"
        onMouseDown={(e) => e.stopPropagation()}
        onSubmit={submit}
      >
        <h2>New Project</h2>
        <div>
          <label className="muted">Project name</label>
          <input
            type="text"
            autoFocus
            placeholder="e.g. Street signs dataset"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ marginTop: 6 }}
          />
        </div>
        {temporary ? (
          <div className="notice" role="note">
            <span className="notice-icon" aria-hidden="true">
              ⚠
            </span>
            <div className="notice-text">
              <strong>Temporary Project</strong>
              <p>
                This project will be permanently deleted{" "}
                {formatHours(ttlHours) || "30 hours"} after creation.
              </p>
              <p>
                All images, annotations, labels, and exported project data will
                be permanently removed.
              </p>
              <p>
                Make sure to export your dataset before the{" "}
                {formatHoursCompound(ttlHours) || "30-hour"} deadline.
              </p>
            </div>
          </div>
        ) : null}
        {error ? <div className="state error" style={{ padding: 0 }}>{error}</div> : null}
        <div className="row between">
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Creating…" : temporary ? "I understand, create" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
