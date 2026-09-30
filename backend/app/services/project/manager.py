from datetime import datetime, timedelta, timezone
import secrets

from app.core import storage
from app.core.config import settings
from app.core.storage_backend import get_backend
from app.models.project import Project


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """Coerce a stored timestamp to an aware UTC datetime.

    Metadata written by older builds (and by local mode) may be naive; treating
    those as UTC keeps comparisons total instead of raising at runtime.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class ProjectManager:
    """Projects persisted as one metadata document plus per-project index docs.

    Storage goes through the active backend (local filesystem in v1.0.0, Supabase
    object storage for the public deployment), so the same manager code drives
    both without changing the logical data model.

    Public (cloud) projects are *temporary*: each is stamped server-side with an
    ``expires_at`` at creation, is treated as already gone once that passes, and
    is hard deleted by :meth:`cleanup_expired_projects`. Local/self-hosted mode
    never stamps an expiry, so nothing there ever expires or is auto-deleted.
    """

    # -- expiry helpers -------------------------------------------------------

    def _expiry_for(self, created_at: datetime) -> datetime | None:
        """The server-side deadline for a project created at ``created_at``.

        Returns ``None`` when expiry does not apply (local mode or TTL disabled),
        which is what keeps self-hosted projects permanent.
        """
        if not settings.project_ttl_enabled:
            return None
        return created_at + timedelta(hours=settings.PROJECT_TTL_HOURS)

    def is_expired(self, project: Project) -> bool:
        """True when a project has passed its stored deadline.

        Driven purely by the stored ``expires_at``, so the answer does not
        change if the configured TTL is edited later, and a client clock has no
        influence at all. Projects without a deadline (local mode) never expire.
        """
        expires_at = _as_utc(project.expires_at)
        if expires_at is None:
            return False
        return _now() >= expires_at

    # -- ownership ------------------------------------------------------------

    def owns(self, project: Project, session_id: str | None) -> bool:
        """Whether ``session_id`` may act on ``project`` under the active policy.

        * Ownership disabled (local/self-hosted, the v1.0.0 path): always True,
          so single-user self-hosting and pre-existing ownerless projects are
          unaffected.
        * Ownership enabled (shared public deployment): True only when the
          project carries an ``owner_id`` that matches this session exactly.
          Legacy projects with no ``owner_id`` are owned by nobody and are never
          silently claimed by whoever asks first. Compared with
          ``compare_digest`` to avoid leaking the match via timing.
        """
        if not settings.owner_scoping_enabled:
            return True
        if not session_id or not project.owner_id:
            return False
        return secrets.compare_digest(project.owner_id, session_id)

    def load_metadata(self, project_id: str) -> Project | None:
        """Cheap ownership/existence load: metadata only, no count refresh.

        Hides expired projects and rejects unsafe ids (via ``_load``). Used by
        the route ownership guard so the hot image-``/file`` path does not pay
        the image+annotation recount that ``get_project`` performs.
        """
        return self._load(project_id)

    def create_project(self, name: str | None = None, owner_id: str | None = None) -> Project:
        created_at = _now()
        project = Project(
            name=(name.strip() if name and name.strip() else "Untitled Project"),
            created_at=created_at,
            updated_at=created_at,
            # Stamped from the server clock only — never from the request.
            expires_at=self._expiry_for(created_at),
            # Stamped from the anonymous session cookie only (see routes); never
            # accepted from a request body, so ownership cannot be spoofed.
            owner_id=owner_id,
        )

        backend = get_backend()

        # Create the project container (dirs locally; a no-op in object storage).
        backend.init_project(project.id)

        # Initialize the index documents so a freshly created project always has
        # the same shape regardless of backend (source of truth is these docs).
        backend.write_doc(project.id, "images", [])
        backend.write_doc(project.id, "labels", [])
        backend.write_doc(project.id, "annotations", [])

        self.save_project(project)
        return project

    def save_project(self, project: Project) -> None:
        get_backend().write_doc(
            project.id,
            "metadata",
            project.model_dump(mode="json"),
        )

    def _load(self, project_id: str, include_expired: bool = False) -> Project | None:
        """Load a project's metadata.

        Expired projects are reported as missing so that every read path (get,
        list, images, labels, annotations, export) treats them as gone the moment
        the deadline passes — even if the cleanup sweep has not run yet. The
        sweep itself passes ``include_expired=True``, since it must still be able
        to see what it is about to delete.
        """
        if not storage.is_safe_id(project_id):
            return None
        data = get_backend().read_doc(project_id, "metadata", None)
        if data is None:
            return None
        try:
            project = Project(**data)
        except Exception:
            return None
        if not include_expired and self.is_expired(project):
            return None
        return project

    def exists(self, project_id: str) -> bool:
        """Cheap existence check that does NOT recompute counts.

        ``get_project`` refreshes image/annotation counts from disk on every
        call, which is wasteful when the caller only needs to know the project
        is present (e.g. the per-file upload path). This reads just the
        metadata and is safe against unsafe ids via ``_load``.
        """
        return self._load(project_id) is not None

    def _refresh_counts(self, project: Project) -> Project:
        """Recompute image/annotation counts from disk so metadata is accurate.

        Counts must match what the API actually serves: the upload and
        annotation managers skip invalid/legacy entries (e.g. old image-level
        labels without bounding-box coordinates) when loading, so counting the
        raw JSON length here would overstate legacy projects. Import locally to
        avoid a circular import at module load.
        """
        from app.services.annotation.manager import manager as annotation_manager
        from app.services.upload.manager import manager as upload_manager

        new_images = len(upload_manager.list_images(project.id))
        new_annotations = len(annotation_manager.list_all(project.id))

        if project.images != new_images or project.annotations != new_annotations:
            project.images = new_images
            project.annotations = new_annotations
            self.save_project(project)

        return project

    def list_projects(self, owner_id: str | None = None) -> list[Project]:
        """List projects, scoped to ``owner_id`` when ownership is enforced.

        In cloud/public mode only the calling session's projects are returned,
        so one browser never sees another's. In local/self-hosted mode ownership
        is disabled and every project is returned, exactly as v1.0.0 did.
        """
        projects: list[Project] = []

        for project_id in get_backend().list_project_ids():
            project = self._load(project_id)
            if project is None:
                continue
            if not self.owns(project, owner_id):
                continue
            projects.append(self._refresh_counts(project))

        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects

    def get_project(self, project_id: str) -> Project | None:
        project = self._load(project_id)
        if project is None:
            return None
        return self._refresh_counts(project)

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        status: str | None = None,
    ) -> Project | None:
        project = self._load(project_id)
        if project is None:
            return None

        if name is not None and name.strip():
            project.name = name.strip()
        if status is not None and status.strip():
            project.status = status.strip()

        project.updated_at = _now()
        self.save_project(project)
        return self._refresh_counts(project)

    def touch_opened(self, project_id: str) -> Project | None:
        project = self._load(project_id)
        if project is None:
            return None
        project.last_opened = _now()
        self.save_project(project)
        return self._refresh_counts(project)

    def seconds_remaining(self, project: Project) -> int | None:
        """Whole seconds until the project expires, computed on the server.

        Returned alongside project payloads so the UI can render a countdown
        without trusting the browser clock. ``None`` means the project has no
        deadline (local/self-hosted mode).
        """
        expires_at = _as_utc(project.expires_at)
        if expires_at is None:
            return None
        return max(0, int((expires_at - _now()).total_seconds()))

    def delete_project(self, project_id: str) -> bool:
        if not storage.is_safe_id(project_id):
            return False
        # An expired project is already "gone" as far as the API is concerned, so
        # deleting it reports not-found; the cleanup sweep owns its removal.
        if self._load(project_id) is None:
            existing = self._load(project_id, include_expired=True)
            if existing is not None and self.is_expired(existing):
                return False
        return get_backend().delete_project(project_id)

    def cleanup_expired_projects(self) -> dict:
        """Permanently delete every project past its deadline (cloud only).

        Public projects are anonymous and temporary, so expired ones are swept to
        keep the free object-storage quota bounded. This is a *simple* on-demand
        sweep meant to be triggered by an external cron hitting the maintenance
        endpoint — not a background job system.

        Properties this relies on:

        * **Cloud only.** A hard no-op in local mode and when the TTL is
          disabled, so a self-hosted user's data is never destroyed.
        * **Scoped.** Deletion goes through ``backend.delete_project(id)``, which
          only ever touches keys under that one project's prefix, so a sweep can
          never remove another project's objects.
        * **Idempotent.** Only projects whose stored deadline has passed are
          removed, and an already-deleted project simply is not listed on the
          next run, so repeated calls converge and report ``deleted: 0``.
        * **Complete.** The backend removes *all* of the project's objects
          (metadata.json, images.json, labels.json, annotations.json and every
          image blob); metadata is not dropped until the rest is handled, so a
          partial failure leaves the project visible-as-expired and therefore
          retryable rather than orphaning unreachable blobs.
        """
        if not settings.project_ttl_enabled:
            return {"enabled": False, "deleted": 0, "checked": 0, "failed": 0}

        backend = get_backend()

        deleted = 0
        checked = 0
        failed = 0
        for project_id in backend.list_project_ids():
            # include_expired: the sweep must see exactly what normal reads hide.
            project = self._load(project_id, include_expired=True)
            if project is None:
                continue
            checked += 1
            if not self.is_expired(project):
                continue
            if backend.delete_project(project_id):
                deleted += 1
            else:
                # Left in place on purpose: it stays expired (invisible to the
                # API) and will be retried by the next sweep.
                failed += 1

        return {
            "enabled": True,
            "deleted": deleted,
            "checked": checked,
            "failed": failed,
        }


manager = ProjectManager()
