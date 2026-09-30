/**
 * Helpers for rendering a project's remaining lifetime.
 *
 * The backend sends `seconds_remaining` alongside every project payload,
 * computed from the stored `expires_at` against the *server* clock. Everything
 * here works from that number and from locally measured elapsed time, so a
 * browser whose clock is wrong (or deliberately changed) can only mis-render
 * the label — it can never move the real deadline, which lives server-side.
 *
 * `seconds_remaining` is null when a project has no deadline at all
 * (local/self-hosted mode); callers render nothing in that case.
 */

/** Human countdown: "29h 42m", "42m", "< 1m". */
export function formatRemaining(seconds) {
  if (seconds === null || seconds === undefined) return "";
  const total = Math.max(0, Math.floor(seconds));
  if (total === 0) return "expired";

  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return "< 1m";
}

/**
 * How loudly the countdown should be shown. The indicator is deliberately
 * quiet for most of a project's life and only becomes prominent as the deadline
 * approaches, so it informs without nagging.
 */
export function expiryTone(seconds) {
  if (seconds === null || seconds === undefined) return null;
  if (seconds <= 0) return "expired";
  if (seconds <= 3600) return "urgent"; // final hour
  if (seconds <= 6 * 3600) return "soon"; // final six hours
  return "calm";
}

/** "30 hours" / "1 hour" — used in the temporary-project warning copy. */
export function formatHours(hours) {
  const n = Number(hours);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n} ${n === 1 ? "hour" : "hours"}`;
}

/** "30-hour" — the adjectival form, as in "the 30-hour deadline". */
export function formatHoursCompound(hours) {
  const n = Number(hours);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n}-hour`;
}
