"""Image preprocessing + dataset validation/splitting.

Normalisation convention (single source of truth):
  * This module returns RGB float32 arrays in the 0-255 range, 224x224x3.
  * The saved Keras model starts with a Rescaling(1/127.5, offset=-1) layer
    (the MobileNetV2 convention), so training and inference are consistent
    and no separate normalisation step can be forgotten at inference time.

CLI:
    python -m machine_learning.preprocessing.preprocess --raw dataset/raw
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from backend.core.config import CLASS_FOLDERS, PROJECT_ROOT

IMG_SIZE = 224
SEED = 42
VALID_EXT = {".jpg", ".jpeg", ".png"}
MIN_SIDE = 64
BLUR_THRESHOLD = 20.0  # variance of Laplacian; below => very blurry


# --------------------------------------------------------------------- inference
def decode_image(data: bytes) -> np.ndarray:
    """Decode bytes -> RGB uint8 array. Raises ValueError if unreadable."""
    arr = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Image could not be decoded.")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def preprocess_rgb(rgb: np.ndarray, size: int = IMG_SIZE) -> np.ndarray:
    """Resize to size x size, float32 0-255, shape (size, size, 3)."""
    resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
    return resized.astype("float32")


def preprocess_bytes(data: bytes, size: int = IMG_SIZE) -> np.ndarray:
    """bytes -> batch of shape (1, size, size, 3) ready for model.predict."""
    return np.expand_dims(preprocess_rgb(decode_image(data), size), axis=0)


# ------------------------------------------------------------- dataset validation
def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_dataset(raw_dir: Path, remove_bad: bool = False) -> dict:
    """Check format, readability, quality, duplicates and class distribution."""
    report: dict = {"classes": {}, "unreadable": [], "too_small": [], "blurry": [], "duplicates": []}
    seen: dict[str, Path] = {}
    for folder in CLASS_FOLDERS:
        cdir = raw_dir / folder
        files = [p for p in sorted(cdir.glob("*")) if p.is_file() and p.name != ".gitkeep"] if cdir.exists() else []
        good = 0
        for p in files:
            if p.suffix.lower() not in VALID_EXT:
                report["unreadable"].append(str(p)); continue
            img = cv2.imread(str(p))
            if img is None:
                report["unreadable"].append(str(p))
                if remove_bad: p.unlink()
                continue
            h, w = img.shape[:2]
            if min(h, w) < MIN_SIDE:
                report["too_small"].append(str(p)); continue
            if cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < BLUR_THRESHOLD:
                report["blurry"].append(str(p))  # flagged for manual review only
            digest = file_md5(p)
            if digest in seen:
                report["duplicates"].append([str(p), str(seen[digest])])
                if remove_bad: p.unlink()
                continue
            seen[digest] = p
            good += 1
        report["classes"][folder] = good
    total = sum(report["classes"].values())
    report["total_valid"] = total
    report["imbalance_ratio"] = (max(report["classes"].values()) / max(1, min(report["classes"].values()))) if total else None
    return report


def split_dataset(raw_dir: Path, out_root: Path, seed: int = SEED,
                  ratios: tuple[float, float, float] = (0.70, 0.15, 0.15)) -> dict[str, dict[str, int]]:
    """Stratified (per-class), reproducible 70/15/15 split into train/validation/test.

    Files are COPIED so raw data is untouched. Exact duplicates (by MD5) are
    excluded first so the same image cannot leak between splits.
    """
    from sklearn.model_selection import train_test_split

    for split in ("train", "validation", "test"):
        for folder in CLASS_FOLDERS:
            d = out_root / split / folder
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    counts: dict[str, dict[str, int]] = {s: {} for s in ("train", "validation", "test")}
    seen: set[str] = set()
    for folder in CLASS_FOLDERS:
        files: list[Path] = []
        for p in sorted((raw_dir / folder).glob("*")):
            if p.suffix.lower() in VALID_EXT and cv2.imread(str(p)) is not None:
                digest = file_md5(p)
                if digest not in seen:
                    seen.add(digest); files.append(p)
        if len(files) < 10:
            raise ValueError(f"Class '{folder}' has only {len(files)} valid images; need at least 10.")
        train, rest = train_test_split(files, test_size=ratios[1] + ratios[2], random_state=seed)
        val, test = train_test_split(rest, test_size=ratios[2] / (ratios[1] + ratios[2]), random_state=seed)
        for split, items in (("train", train), ("validation", val), ("test", test)):
            for p in items:
                shutil.copy2(p, out_root / split / folder / p.name)
            counts[split][folder] = len(items)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(PROJECT_ROOT / "dataset" / "raw"))
    ap.add_argument("--out", default=str(PROJECT_ROOT / "dataset"))
    ap.add_argument("--remove-bad", action="store_true", help="delete unreadable/duplicate files from raw")
    ap.add_argument("--split", action="store_true", help="also create train/validation/test split")
    a = ap.parse_args()
    rep = validate_dataset(Path(a.raw), remove_bad=a.remove_bad)
    print(json.dumps(rep, indent=2))
    out = Path(a.out)
    (out / "processed").mkdir(parents=True, exist_ok=True)
    (out / "processed" / "dataset_report.json").write_text(json.dumps(rep, indent=2))
    if a.split:
        print(json.dumps(split_dataset(Path(a.raw), out), indent=2))


if __name__ == "__main__":
    main()
