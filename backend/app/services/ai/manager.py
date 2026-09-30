"""AI auto-labeling service boundary.

This defines the interface for future automatic annotation (e.g. YOLOv8).
It is intentionally NOT wired to a real model yet: no fake predictions are
returned. The route layer calls ``manager.is_available()`` and reports an
honest "not implemented" response until a model is integrated here.

To add real inference later:
  1. Add the model dependency (e.g. ``ultralytics``) to requirements.txt.
  2. Load a lightweight pretrained model in ``_load_model`` (cache it).
  3. Run inference in ``predict`` and convert results to ``AnnotationIn``
     objects with normalized (x, y, width, height) coordinates.
"""

from app.models.annotation import AnnotationIn
from app.models.image import Image


class AIManager:
    def __init__(self) -> None:
        self._model = None

    def is_available(self) -> bool:
        # Flip to True once a real model is loaded in _load_model().
        return False

    def _load_model(self):  # pragma: no cover - not implemented yet
        raise NotImplementedError(
            "AI auto-labeling is not implemented yet. "
            "See backend/app/services/ai/manager.py for integration steps."
        )

    def predict(self, project_id: str, image: Image) -> list[AnnotationIn]:
        """Return predicted bounding boxes for an image.

        Not implemented. Raises so the API can return an honest error rather
        than fabricating annotations.
        """
        raise NotImplementedError(
            "AI auto-labeling is not implemented yet."
        )


manager = AIManager()
