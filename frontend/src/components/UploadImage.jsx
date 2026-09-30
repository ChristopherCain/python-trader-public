import { useRef, useState } from "react";

import { uploadImages } from "../api/imageApi";

const ACCEPT = ".jpg,.jpeg,.png,.webp";
const ALLOWED = ["image/jpeg", "image/png", "image/webp"];

export default function UploadImage({ projectId, onUploaded, onError }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;

    // Client-side validation; the backend validates again authoritatively.
    const valid = files.filter(
      (f) => ALLOWED.includes(f.type) || /\.(jpe?g|png|webp)$/i.test(f.name)
    );
    const invalidCount = files.length - valid.length;

    if (valid.length === 0) {
      onError?.("Only JPG, PNG and WEBP images are supported.");
      return;
    }

    setBusy(true);
    setProgress(0);
    try {
      const result = await uploadImages(projectId, valid, setProgress);
      const skipped = (result?.skipped?.length || 0) + invalidCount;
      onUploaded?.(result?.uploaded || [], skipped);
    } catch (err) {
      onError?.(err.message || "Upload failed.");
    } finally {
      setBusy(false);
      setProgress(0);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className={"uploader" + (busy ? " busy" : "")}>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />
      <button
        className="primary small"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "Uploading…" : "+ Upload Images"}
      </button>
      <div className="hint" style={{ marginTop: 6 }}>
        JPG, PNG or WEBP
      </div>
      {busy ? (
        <div className="progress">
          <span style={{ width: `${progress}%` }} />
        </div>
      ) : null}
    </div>
  );
}
