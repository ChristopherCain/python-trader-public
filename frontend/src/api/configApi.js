import api, { request } from "./api";

/**
 * Public runtime configuration reported by the backend.
 *
 * The same frontend build runs against a self-hosted backend (projects are
 * permanent) and against the free public deployment (projects expire), so the
 * expiry warning must be driven by what the server says rather than by a
 * build-time flag or a guess based on the URL.
 */
export const getConfig = () => request(api.get("/config"));
