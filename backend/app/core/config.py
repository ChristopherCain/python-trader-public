from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/app/core/config.py -> parents[2] == backend/
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Read a local .env when present (handy for dev); ignore unknown vars so a
    # shared deployment environment can carry extra keys without crashing here.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ForgoteLabeling API"
    VERSION: str = "1.0.0"

    BASE_DIR: Path = BASE_DIR

    # All local storage derives from BASE_DIR so the app behaves the same
    # regardless of the directory uvicorn is started from.
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    EXPORT_DIR: Path = BASE_DIR / "exports"
    PROJECT_DIR: Path = BASE_DIR / "projects"
    CHECKPOINT_DIR: Path = BASE_DIR / "checkpoints"

    # Allowed image types for uploads.
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

    # -----------------------------------------------------------------
    # Storage backend selection
    # -----------------------------------------------------------------
    # "local"  -> JSON + image files on the local filesystem (v1.0.0 default,
    #             used for self-hosting and the whole test suite).
    # "cloud"  -> objects in Supabase Storage, for the ephemeral-disk public
    #             deployment. Selected only when STORAGE_BACKEND=cloud is set.
    STORAGE_BACKEND: str = "cloud"

    # Supabase Storage config (only required when STORAGE_BACKEND=cloud).
    # SUPABASE_SERVICE_KEY is a secret and must come from the environment; it is
    # used server-side only and never sent to the browser.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "projects"

    # Shared secret guarding the on-demand cleanup endpoint. When empty (the
    # default, and always in local mode) the endpoint is disabled entirely, so a
    # self-hosted instance never exposes it. Set from the environment in cloud.
    MAINTENANCE_TOKEN: str = ""

    # -----------------------------------------------------------------
    # Anonymous per-browser project ownership
    # -----------------------------------------------------------------
    # No login/signup: each browser gets a cryptographically random anonymous
    # session id stored in an HttpOnly cookie, and a project is owned by the
    # session that created it. Enforced automatically on the shared public
    # deployment (cloud) so one browser cannot see/touch another's projects.
    #
    # Name of the HttpOnly session cookie. Kept generic (no product/user hint).
    SESSION_COOKIE_NAME: str = "fl_sid"

    # SameSite policy for the session cookie. The public deployment serves the
    # SPA (Cloudflare Pages) and the API (Render) from *different sites*, and
    # image thumbnails load as cross-site ``<img>`` subresources, so the cookie
    # must ride cross-site requests — that requires ``SameSite=None``, which
    # browsers only honor together with ``Secure``. ``None`` + ``Secure`` also
    # works on ``http://localhost`` / ``http://127.0.0.1`` (treated as secure
    # contexts), so local dev is unaffected. Override to ``lax``/``strict`` for a
    # same-site or plain-http LAN self-host.
    COOKIE_SAMESITE: str = "none"

    # Whether the session cookie is marked ``Secure``. ``auto`` (the default)
    # resolves to ``True``, which localhost still accepts and which is required
    # whenever COOKIE_SAMESITE is ``none``. Set to ``false`` ONLY for a
    # self-hosted instance served over plain http on a non-localhost host.
    COOKIE_SECURE: str = "auto"

    # How long (seconds) the anonymous session cookie persists, so a browser
    # keeps its projects across restarts. Defaults to ~1 year; the cloud TTL
    # deletes the underlying projects far sooner anyway.
    SESSION_COOKIE_MAX_AGE: int = 60 * 60 * 24 * 365

    # Whether project ownership is enforced. ``auto`` (default) enforces it in
    # cloud mode (the shared public deployment, where privacy is required) and
    # leaves local/self-hosted mode exactly as v1.0.0 (no scoping), so existing
    # ownerless projects and single-user workflows keep working. Force with
    # ``on``/``off``.
    OWNERSHIP_MODE: str = "auto"

    # -----------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------
    # Local dev origins are always allowed. The deployed frontend origin is
    # added via FRONTEND_ORIGIN (e.g. https://your-project.pages.dev) so we
    # never need a wildcard origin alongside credentials.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    FRONTEND_ORIGIN: str = ""

    # -----------------------------------------------------------------
    # Abuse limits for anonymous public projects
    # -----------------------------------------------------------------
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024          # 10 MB per image
    MAX_IMAGES_PER_PROJECT: int = 100                 # images per project
    MAX_PROJECT_BYTES: int = 200 * 1024 * 1024        # total bytes per project

    # -----------------------------------------------------------------
    # Temporary-project lifetime (cloud only)
    # -----------------------------------------------------------------
    # Public projects are anonymous and disposable: the free object-storage quota
    # is finite, so each project is stamped with an expiry at creation and hard
    # deleted once it passes. 0 or a negative value disables expiry entirely.
    # NEVER applied in local mode, so self-hosted data is never auto-deleted.
    PROJECT_TTL_HOURS: int = 30

    @property
    def project_ttl_enabled(self) -> bool:
        """True when projects should be stamped with (and checked against) a TTL.

        Cloud-only by design: expiry is a consequence of the free-tier public
        deployment, not of the product itself.
        """
        return self.is_cloud and self.PROJECT_TTL_HOURS > 0

    @property
    def all_cors_origins(self) -> list[str]:
        """Local dev origins plus the deployed frontend origin, if configured."""
        origins = list(self.CORS_ORIGINS)
        if self.FRONTEND_ORIGIN and self.FRONTEND_ORIGIN not in origins:
            origins.append(self.FRONTEND_ORIGIN)
        return origins

    @property
    def is_cloud(self) -> bool:
        return self.STORAGE_BACKEND.strip().lower() == "cloud"

    @property
    def session_cookie_secure(self) -> bool:
        """Whether the session cookie is sent with the ``Secure`` attribute.

        ``auto`` resolves to ``True`` (required when SameSite=None, and still
        accepted by browsers over http://localhost). Any explicit truthy string
        forces it on; ``false``/``0``/``no``/``off`` forces it off for a
        plain-http LAN self-host.
        """
        value = self.COOKIE_SECURE.strip().lower()
        if value in ("", "auto"):
            return True
        return value in ("1", "true", "yes", "on")

    @property
    def owner_scoping_enabled(self) -> bool:
        """Whether project ownership is enforced (cloud-only by default).

        Local/self-hosted mode is left unscoped so v1.0.0 behavior and existing
        ownerless projects are preserved; the shared public deployment enforces
        per-browser ownership so projects are private.
        """
        mode = self.OWNERSHIP_MODE.strip().lower()
        if mode == "on":
            return True
        if mode == "off":
            return False
        return self.is_cloud


settings = Settings()


def ensure_storage_dirs() -> None:
    """Create the local storage directories if they do not exist.

    A no-op for the cloud backend, which has no local persistent disk (object
    storage keys are created implicitly on first write).
    """
    if settings.is_cloud:
        return
    for directory in (
        settings.UPLOAD_DIR,
        settings.EXPORT_DIR,
        settings.PROJECT_DIR,
        settings.CHECKPOINT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
