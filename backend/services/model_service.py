"""Singleton access to the predictor (overridable in tests via FastAPI dependency)."""
from __future__ import annotations

from backend.core.config import settings
from machine_learning.inference.predictor import PoultryPredictor

_predictor: PoultryPredictor | None = None


def get_predictor() -> PoultryPredictor:
    global _predictor
    if _predictor is None:
        cfg = settings()
        _predictor = PoultryPredictor(cfg.model_path, cfg.class_names_path, cfg.model_metadata_path)
    return _predictor


def reset_predictor() -> None:
    global _predictor
    _predictor = None
