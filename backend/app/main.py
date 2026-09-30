from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import ensure_storage_dirs, settings
from app.core.session import (
    is_valid_session_id,
    new_session_id,
    set_session_cookie,
)
from app.utils.responses import error

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
)

# Explicit origins so credentialed requests are valid (a wildcard origin
# combined with credentials is rejected by browsers). ``all_cors_origins``
# adds the deployed frontend origin (FRONTEND_ORIGIN) to the local dev origins
# when it is configured, so production never needs a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers hide every response header from cross-origin JS unless it is
    # named here. The dataset export is fetched over XHR so the UI can show a
    # loading state, and it reads the download filename from this header; the
    # frontend falls back to a generated name, but exposing it keeps the served
    # filename authoritative. Response *bodies* are unaffected.
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def anonymous_session_middleware(request: Request, call_next):
    """Give every browser a stable anonymous session id via an HttpOnly cookie.

    On the first request from a browser (no valid session cookie yet) a
    cryptographically random id is minted, stashed on ``request.state`` so route
    handlers and the ownership check can read it, and written back as an HttpOnly
    cookie on the response. Returning browsers simply reuse the cookie value.

    The id is derived *only* from the cookie here — never from a request body,
    header, or query parameter — so ownership cannot be spoofed by the client.
    No id is ever placed in a response body, so page JavaScript never sees it.
    """
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if is_valid_session_id(raw):
        session_id = raw
        minted = False
    else:
        session_id = new_session_id()
        minted = True

    request.state.session_id = session_id
    response = await call_next(request)

    # Only send Set-Cookie when we minted a new id, so we do not rewrite the
    # cookie (and its expiry) on every single request.
    if minted:
        set_session_cookie(response, session_id)
    return response


@app.exception_handler(RequestValidationError)
def _on_validation_error(request: Request, exc: RequestValidationError):
    """Return request-validation failures in the app's standard envelope.

    FastAPI's default handler returns a bare ``{"detail": [...]}`` at HTTP 422,
    which is inconsistent with every other endpoint's
    ``{"success", "message", "error"}`` shape. We keep the 422 status and the
    original error list (under ``error.detail``) so clients that already read
    ``detail`` still work, while new clients can rely on the envelope. Successful
    responses are unchanged.
    """
    return error(
        "Request validation failed.",
        422,
        {"detail": jsonable_encoder(exc.errors())},
    )


@app.on_event("startup")
def _startup() -> None:
    ensure_storage_dirs()


app.include_router(router)
