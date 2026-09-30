from app.core import storage
from app.core.storage_backend import get_backend
from app.models.label import DEFAULT_COLORS, Label


class LabelError(Exception):
    """Raised for invalid label operations (e.g. duplicate names)."""


class LabelManager:
    """Project-specific labels / classes, persisted to labels.json."""

    def _load(self, project_id: str) -> list[Label]:
        if not storage.is_safe_id(project_id):
            return []
        raw = get_backend().read_doc(project_id, "labels", [])
        labels: list[Label] = []
        for item in raw:
            try:
                labels.append(Label(**item))
            except Exception:
                continue
        return labels

    def _save(self, project_id: str, labels: list[Label]) -> None:
        get_backend().write_doc(
            project_id,
            "labels",
            [label.model_dump(mode="json") for label in labels],
        )

    def list_labels(self, project_id: str) -> list[Label]:
        return self._load(project_id)

    def get_label(self, project_id: str, label_id: str) -> Label | None:
        for label in self._load(project_id):
            if label.id == label_id:
                return label
        return None

    def create_label(
        self,
        project_id: str,
        name: str,
        color: str | None = None,
    ) -> Label:
        name = (name or "").strip()
        if not name:
            raise LabelError("Label name cannot be empty.")

        labels = self._load(project_id)

        if any(label.name.lower() == name.lower() for label in labels):
            raise LabelError(f"Label '{name}' already exists in this project.")

        if not color:
            color = DEFAULT_COLORS[len(labels) % len(DEFAULT_COLORS)]

        label = Label(project_id=project_id, name=name, color=color)
        labels.append(label)
        self._save(project_id, labels)
        return label

    def update_label(
        self,
        project_id: str,
        label_id: str,
        name: str | None = None,
        color: str | None = None,
    ) -> Label | None:
        labels = self._load(project_id)

        if name and name.strip():
            clean = name.strip()
            if any(
                other.id != label_id and other.name.lower() == clean.lower()
                for other in labels
            ):
                raise LabelError(f"Label '{clean}' already exists in this project.")

        for label in labels:
            if label.id == label_id:
                if name and name.strip():
                    label.name = name.strip()
                if color:
                    label.color = color
                self._save(project_id, labels)
                return label

        return None

    def delete_label(self, project_id: str, label_id: str) -> bool:
        labels = self._load(project_id)
        remaining = [label for label in labels if label.id != label_id]

        if len(remaining) == len(labels):
            return False

        self._save(project_id, remaining)
        return True


manager = LabelManager()
