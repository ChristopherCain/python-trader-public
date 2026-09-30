import { useEffect, useRef, useState } from "react";

import { expiryTone, formatRemaining } from "../utils/expiry";

/**
 * Subtle "Expires in 29h 42m" indicator for temporary (public) projects.
 *
 * Renders nothing when `seconds` is null/undefined, which is how a self-hosted
 * project — one with no deadline — stays visually unchanged from v1.0.0.
 *
 * The ticking is display only. It starts from the server's `seconds_remaining`
 * and subtracts locally *elapsed* time, so the label stays honest without ever
 * trusting the browser's wall clock. Deletion is decided solely by the backend;
 * when the countdown reaches zero we just ask the caller to re-fetch (via
 * `onExpire`) and let the server's answer be the truth.
 *
 * Props:
 *   seconds   server-computed seconds remaining at fetch time (null = never)
 *   onExpire  optional; called once when the local countdown hits zero
 */
export default function ExpiryBadge({ seconds, onExpire }) {
  const [left, setLeft] = useState(seconds);
  const firedRef = useRef(false);

  useEffect(() => {
    setLeft(seconds);
    firedRef.current = false;

    if (seconds === null || seconds === undefined) return;

    const startedAt = Date.now();
    const initial = Math.max(0, Math.floor(seconds));

    const tick = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setLeft(Math.max(0, initial - elapsed));
    };

    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [seconds]);

  useEffect(() => {
    if (left === 0 && !firedRef.current && seconds !== null && seconds !== undefined) {
      firedRef.current = true;
      onExpire?.();
    }
  }, [left, seconds, onExpire]);

  if (left === null || left === undefined) return null;

  const tone = expiryTone(left);
  const label =
    left <= 0 ? "Expired — removing" : `Expires in ${formatRemaining(left)}`;

  return (
    <span className={`expiry expiry-${tone}`} title="Temporary project">
      <span className="expiry-dot" aria-hidden="true" />
      {label}
    </span>
  );
}
