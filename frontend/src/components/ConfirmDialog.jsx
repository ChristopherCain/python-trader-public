import { useEffect, useRef, useState } from "react";

/**
 * In-app confirmation dialog — the replacement for `window.confirm`.
 *
 * Native `confirm()` blocks the JS thread, can't be styled, and looks foreign
 * next to the rest of the UI. This renders the same yes/no decision as a
 * regular modal so it matches the app's theme and can show async progress
 * while the action runs.
 *
 * Props:
 *   title       heading, e.g. "Delete project"
 *   message     body text; `highlight` is rendered emphasized after it
 *   highlight   the subject of the action (project/image name)
 *   note        optional smaller caveat line, e.g. "This cannot be undone."
 *   confirmText label for the destructive button (default "Delete")
 *   onConfirm   async fn; the dialog shows a busy state until it settles
 *   onCancel    close without acting
 */
export default function ConfirmDialog({
  title = "Are you sure?",
  message = "",
  highlight = "",
  note = "This cannot be undone.",
  confirmText = "Delete",
  onConfirm,
  onCancel,
}) {
  const [busy, setBusy] = useState(false);
  const confirmRef = useRef(null);

  // Escape cancels; focus starts on the confirm button so the dialog is
  // fully keyboard-operable (Enter confirms, Esc dismisses).
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", onKey);
    confirmRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel, busy]);

  async function confirm() {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      // The parent unmounts us on success; resetting keeps the dialog usable
      // if the action failed and it stayed open.
      setBusy(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      onMouseDown={() => {
        if (!busy) onCancel();
      }}
    >
      <div
        className="modal confirm"
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <span className="modal-icon" aria-hidden="true">
          ⚠
        </span>
        <h2>{title}</h2>
        <p className="modal-body">
          {message} {highlight ? <strong>{highlight}</strong> : null}
          {note ? (
            <>
              <br />
              {note}
            </>
          ) : null}
        </p>
        <div className="modal-actions">
          <button type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            ref={confirmRef}
            className="danger-solid"
            onClick={confirm}
            disabled={busy}
          >
            {busy ? "Deleting…" : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
