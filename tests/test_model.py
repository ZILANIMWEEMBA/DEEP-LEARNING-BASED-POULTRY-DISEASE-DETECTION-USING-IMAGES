import numpy as np
import pytest

from backend.core.config import CLASS_FOLDERS, CLASS_NAMES
from backend.core.exceptions import ModelUnavailableError, PredictionFailure
from machine_learning.evaluation.evaluate import compute_metrics
from machine_learning.inference.predictor import PoultryPredictor, build_result
from machine_learning.preprocessing.preprocess import decode_image, preprocess_bytes
from tests.conftest import make_image


def test_class_mapping_is_fixed():
    assert CLASS_NAMES == ["Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"]
    assert len(CLASS_FOLDERS) == 4 and CLASS_FOLDERS[2] == "Newcastle_Disease"


@pytest.mark.parametrize("fmt", ["JPEG", "PNG"])
def test_preprocess_shape_and_range(fmt):
    batch = preprocess_bytes(make_image(fmt, (300, 200)))
    assert batch.shape == (1, 224, 224, 3) and batch.dtype == np.float32
    assert 0 <= batch.min() and batch.max() <= 255


def test_decode_rejects_garbage():
    with pytest.raises(ValueError):
        decode_image(b"not an image")


def test_build_result_probabilities():
    r = build_result(np.array([0.03, 0.91, 0.04, 0.02]))
    assert r["predicted_class"] == "Coccidiosis" and r["confidence"] == pytest.approx(0.91)
    assert list(r["probabilities"]) == CLASS_NAMES
    assert sum(r["probabilities"].values()) == pytest.approx(1.0)


def test_build_result_requires_a_clear_winner():
    r = build_result(np.array([0.90, 0.04, 0.03, 0.03]))
    assert r["predicted_class"] == "Healthy"
    assert r["confidence"] == pytest.approx(0.90)
    assert all(v <= 0.05 for k, v in r["probabilities"].items() if k != "Healthy")
    with pytest.raises(PredictionFailure):
        build_result(np.array([0.14, 0.47, 0.26, 0.13]))


def test_build_result_rejects_bad_distribution():
    with pytest.raises(PredictionFailure):
        build_result(np.array([0.5, 0.5, 0.5, 0.5]))
    with pytest.raises(PredictionFailure):
        build_result(np.array([0.5, 0.5]))


def test_model_unavailable_when_not_trained(tmp_path):
    p = PoultryPredictor(tmp_path / "missing.h5", tmp_path / "c.json")
    assert p.is_available() is False
    with pytest.raises(ModelUnavailableError):
        p.predict(make_image())


def test_training_loss_factory_is_tf_compatible():
    pytest.importorskip("tensorflow")
    from machine_learning.training.train import build_loss
    loss = build_loss(0.05)
    assert loss is not None
    assert hasattr(loss, "__call__")


def test_metrics_computation():
    y = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    m = compute_metrics(y, y)
    assert m["accuracy"] == 1.0 and m["macro"]["f1"] == 1.0
    assert np.array(m["confusion_matrix"]).shape == (4, 4)


def test_real_model_loading_if_present():
    from backend.core.config import settings  # noqa: F401
    from backend.core.config import PROJECT_ROOT
    path = PROJECT_ROOT / "model" / "poultry_mobilenetv2.h5"
    if not path.exists():
        pytest.skip("No trained model present (train first).")
    tf = pytest.importorskip("tensorflow")  # noqa: F841
    p = PoultryPredictor(path, PROJECT_ROOT / "model" / "class_names.json")
    out = p.predict(make_image())
    assert sum(out["probabilities"].values()) == pytest.approx(1.0, abs=1e-3)
