import axios from "axios";

// Base URL for the FastAPI backend.
//   - Public deployment: set VITE_API_BASE_URL to the deployed backend origin
//     (e.g. https://forgotelabeling-api.onrender.com) at build time.
//   - Local dev: leave both unset and it falls back to the local backend.
// VITE_API_URL is still honored for backward compatibility with v1.0.0 setups.
const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

// `withCredentials: true` so the browser sends (and stores) the HttpOnly
// anonymous-session cookie the backend uses for per-browser project ownership.
// Without it, cross-site XHR to the deployed API would omit the cookie and every
// request would look like a brand-new browser. The backend must therefore NOT
// use a wildcard CORS origin (it echoes the specific FRONTEND_ORIGIN); the two
// settings go together.
const api = axios.create({ baseURL, withCredentials: true });

export const API_BASE = baseURL;

/**
 * Unwrap the backend's standard response envelope:
 *   { success, message, data | error }
 *
 * Returns `data` on success, throws an Error with a useful message otherwise.
 */
export async function request(promise) {
  try {
    const res = await promise;
    const body = res.data;

    if (body && typeof body === "object" && "success" in body) {
      if (body.success) return body.data;
      throw new Error(body.message || "Request failed.");
    }
    // Non-enveloped response (e.g. file download) — return as-is.
    return body;
  } catch (err) {
    if (err.response && err.response.data && err.response.data.message) {
      throw new Error(err.response.data.message);
    }
    if (err.message) throw err;
    throw new Error("Network error. Is the backend running?");
  }
}

export default api;
