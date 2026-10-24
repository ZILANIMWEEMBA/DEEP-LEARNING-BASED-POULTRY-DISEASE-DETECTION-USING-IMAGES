"""Dataset validation/splitting logic, using throw-away synthetic images created in tmp_path
purely to test the code (never used for training or reported as results)."""
import cv2
import numpy as np

from backend.core.config import CLASS_FOLDERS
from machine_learning.preprocessing.preprocess import split_dataset, validate_dataset


def _make(root, n=20):
    rng = np.random.default_rng(0)
    for c in CLASS_FOLDERS:
        (root / c).mkdir(parents=True)
        for i in range(n):
            cv2.imwrite(str(root / c / f"{i}.png"), rng.integers(0, 255, (80, 80, 3), dtype="uint8"))


def test_validation_detects_bad_files_and_duplicates(tmp_path):
    raw = tmp_path / "raw"; _make(raw, 12)
    (raw / "Healthy" / "broken.jpg").write_bytes(b"not an image")
    (raw / "Healthy" / "dup.png").write_bytes((raw / "Healthy" / "0.png").read_bytes())
    rep = validate_dataset(raw)
    assert len(rep["unreadable"]) == 1 and len(rep["duplicates"]) == 1
    assert rep["classes"]["Healthy"] == 12


def test_split_is_70_15_15_reproducible_and_leak_free(tmp_path):
    raw = tmp_path / "raw"; _make(raw, 20)
    c1 = split_dataset(raw, tmp_path / "a")
    c2 = split_dataset(raw, tmp_path / "b")
    assert c1 == c2                                           # fixed seed => reproducible
    assert c1["train"]["Healthy"] == 14 and c1["validation"]["Healthy"] == 3 and c1["test"]["Healthy"] == 3
    names = {s: {p.name for f in CLASS_FOLDERS for p in (tmp_path / "a" / s / f).iterdir()}
             for s in ("train", "validation", "test")}
    assert not (names["train"] & names["test"]) or True      # names repeat across classes; check per class:
    for f in CLASS_FOLDERS:
        sets = [{p.name for p in (tmp_path / "a" / s / f).iterdir()} for s in ("train", "validation", "test")]
        assert not (sets[0] & sets[1]) and not (sets[0] & sets[2]) and not (sets[1] & sets[2])
