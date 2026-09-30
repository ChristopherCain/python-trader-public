import api, { API_BASE } from "./api";

// Kept for callers that just need the endpoint URL (e.g. copy-link / debugging).
export const yoloExportUrl = (projectId) =>
  `${API_BASE}/projects/${projectId}/export/yolo`;

/**
 * Read a useful message out of a failed blob request.
 *
 * With `responseType: "blob"` the error body arrives as a Blob rather than
 * parsed JSON, so the backend's `{success, message}` envelope has to be read
 * back as text. Without this the user would only ever see a generic axios
 * string like "Request failed with status code 404".
 */
async function exportErrorMessage(err) {
  const body = err?.response?.data;
  if (body && typeof body.text === "function") {
    try {
      const parsed = JSON.parse(await body.text());
      if (parsed && parsed.message) return parsed.message;
    } catch {
      // Not JSON (or unreadable) — fall through to the generic messages.
    }
  }
  if (err?.response?.status === 404) return "Project not found.";
  if (err?.response) return `Export failed (HTTP ${err.response.status}).`;
  return "Export failed. Is the backend running?";
}

/**
 * Reduce a project name to something safe to use as a download filename.
 * Only needed for the fallback path — the server sends its own sanitized name.
 */
function safeFilenameStem(name) {
  const cleaned = String(name || "")
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "-") // characters filesystems reject
    .replace(/\s+/g, "_")
    .slice(0, 60);
  return cleaned || "dataset";
}

/**
 * Download a dataset export ZIP for a project and hand it to the browser.
 *
 * Fetched over XHR instead of pointing a link at the endpoint, because a link
 * click gives the UI nothing to work with: the browser owns the request, so
 * there is no way to show progress while the archive is built and a failure
 * either navigates away from the workspace or silently drops a JSON error file
 * into the user's downloads. Fetching the blob ourselves means the caller can
 * await it, show a loading state, and report a real error message.
 *
 * `format` is the backend's export path segment ("yolo" or "coco"); both
 * endpoints return a ZIP with identical semantics, so one code path serves both.
 */
export async function downloadExport(
  projectId,
  format = "yolo",
  fallbackName = "dataset"
) {
  let res;
  try {
    res = await api.get(`/projects/${projectId}/export/${format}`, {
      responseType: "blob",
    });
  } catch (err) {
    throw new Error(await exportErrorMessage(err));
  }

  // Prefer the server's filename; it is only readable cross-origin because the
  // API exposes Content-Disposition, so keep a sane fallback either way.
  const disposition = res.headers?.["content-disposition"] || "";
  const match = /filename\*?=(?:UTF-8'')?"?([^\";]+)"?/i.exec(disposition);
  const filename = match
    ? decodeURIComponent(match[1])
    : `${safeFilenameStem(fallbackName)}_${format}.zip`;

  const url = window.URL.createObjectURL(res.data);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    // Release the blob once the download has been handed off, so a few large
    // exports in one session cannot pin the archives in memory.
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }

  return filename;
}

export const downloadYoloExport = (projectId, fallbackName) =>
  downloadExport(projectId, "yolo", fallbackName);

export const downloadCocoExport = (projectId, fallbackName) =>
  downloadExport(projectId, "coco", fallbackName);
