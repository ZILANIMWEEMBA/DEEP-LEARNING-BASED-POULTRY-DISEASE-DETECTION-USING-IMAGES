"""Inference service. Lazily loads the trained Keras model.

If the model file is missing/invalid, ModelUnavailableError is raised - the
application NEVER returns fabricated predictions.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np

from backend.core.config import CLASS_NAMES
from backend.core.exceptions import ModelUnavailableError, PredictionFailure
from machine_learning.preprocessing.preprocess import preprocess_bytes


class PoultryPredictor:
    def __init__(self, model_path: Path, class_names_path: Path, metadata_path: Path | None = None):
        self.model_path = Path(model_path)
        self.class_names_path = Path(class_names_path)
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self._model = None
        self._lock = threading.Lock()
        self.class_names: list[str] = list(CLASS_NAMES)

    # -------------------------------------------------------------- status
    def metadata(self) -> dict | None:
        if self.metadata_path and self.metadata_path.exists():
            try:
                return json.loads(self.metadata_path.read_text())
            except json.JSONDecodeError:
                return None
        return None

    @property
    def version(self) -> str | None:
        meta = self.metadata()
        return (meta or {}).get("version") or (meta or {}).get("created_at")

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except ModelUnavailableError:
            return False

    # -------------------------------------------------------------- loading
    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not self.model_path.exists():
                raise ModelUnavailableError(
                    "The AI model has not been trained or installed yet. Please contact the administrator.")
            if self.class_names_path.exists():
                names = json.loads(self.class_names_path.read_text())
                if names != CLASS_NAMES:
                    raise ModelUnavailableError("Model class mapping does not match the system class mapping.")
            try:
                import tensorflow as tf  # heavy import kept lazy
                self._model = tf.keras.models.load_model(self.model_path, compile=False)
            except Exception as exc:  # noqa: BLE001
                raise ModelUnavailableError("The AI model could not be loaded.") from exc
            if self._model.output_shape[-1] != len(CLASS_NAMES):
                self._model = None
                raise ModelUnavailableError("Model output size does not match the four disease classes.")

    # ----------------------------------------------------------- prediction
    def predict(self, image_bytes: bytes) -> dict:
        self._ensure_loaded()
        try:
            batch = preprocess_bytes(image_bytes)
            probs = np.asarray(self._model.predict(batch, verbose=0)[0], dtype="float64")
        except ModelUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PredictionFailure("Prediction failed. Please try again with another image.") from exc
        return build_result(probs)


def build_result(probs: np.ndarray) -> dict:
    """Convert a probability vector (canonical class order) into the API result.

    The app should never report a diagnosis when the model output is still
    ambiguous. A healthy image should end up with a dominant winner and all other
    classes should be much smaller; weak distributions are rejected so the user is
    not shown a false disease label.
    """
    probs = np.asarray(probs, dtype="float64")
    if probs.shape != (len(CLASS_NAMES),) or not np.isclose(probs.sum(), 1.0, atol=1e-3):
        raise PredictionFailure("Model returned an invalid probability distribution.")

    top = float(probs.max())
    runner_up = float(np.partition(probs, -2)[-2])
    if top >= 0.45 and runner_up >= 0.20 and (top - runner_up) <= 0.25:
        raise PredictionFailure(
            "Model output is not a clear winner. Please retrain with cleaner data or use a clearer image."
        )

    idx = int(np.argmax(probs))
    return {
        "predicted_class": CLASS_NAMES[idx],
        "confidence": float(probs[idx]),
        "probabilities": {name: float(probs[i]) for i, name in enumerate(CLASS_NAMES)},
    }
