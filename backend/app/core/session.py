"""Anonymous per-browser session identity.

No login, no signup, no accounts. Each browser is given a cryptographically
random anonymous session id the first time it is seen; the id lives only in an
HttpOnly cookie (never in a response body, never readable by JavaScript) and is
what project ownership is keyed on.

The id is read from / written to the cookie exclusively by the middleware and
exposed to route handlers through :func:`current_session`, which reads it off
``request.state``. Because the session is derived only from the cookie, a
request body, header, or query parameter can never override it.
"""

from __future__ import annotations

import secrets
import string

from fastapi import Request
from starlette.responses import Response

from app.core.config import settings

# 32 bytes of entropy, URL-safe base64 (~43 chars). More than enough to make a
# session id unguessable; token_urlsafe uses secrets under the hood.
_SESSION_ID_BYTES = 32

# The exact alphabet token_urlsafe can emit (base64url, no padding). Used to
# validate an incoming cookie so a malformed/injected value is treated as "no
# session" and a fresh one is minted instead of trusting arbitrary input.
_ALLOWED_CHARS = set(string.ascii_letters + string.digits + "-_")

# Reasonable bounds for a token_urlsafe(32) value; reject anything wildly off.
_MIN_LEN = 32
_MAX_LEN = 128


def new_session_id() -> str:
    """Return a fresh, cryptographically secure anonymous session id."""
    return secrets.token_urlsafe(_SESSION_ID_BYTES)


def is_valid_session_id(value: str | None) -> bool:
    """True when ``value`` looks like an id we minted.

    This is a shape/whitelist check, not authentication: it only decides whether
    to reuse the cookie or mint a new one. Ownership is still enforced by exact
    comparison against the stored ``owner_id`` elsewhere.
    """
    if not value:
        return False
    if not (_MIN_LEN <= len(value) <= _MAX_LEN):
        return False
    return all(c in _ALLOWED_CHARS for c in value)


def set_session_cookie(response: Response, session_id: str) -> None:
    """Attach the HttpOnly anonymous-session cookie to ``response``.

    HttpOnly so page JavaScript cannot read the id; ``SameSite``/``Secure`` come
    from settings (``None``+``Secure`` in the cross-site public deployment, which
    still works on localhost). ``path=/`` so it is sent to every API route,
    including the image ``/file`` subresource requests.
    """
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.COOKIE_SAMESITE.strip().lower(),
        path="/",
    )


def current_session(request: Request) -> str:
    """FastAPI dependency: the current browser's anonymous session id.

    Read only from ``request.state`` (populated by the session middleware from
    the cookie), so no client-supplied body/header/query value can influence it.
    Returns ``""`` if for some reason the middleware did not run.
    """
    return getattr(request.state, "session_id", "") or ""
