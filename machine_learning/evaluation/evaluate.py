"""Evaluate the trained model on the isolated 15% test split.

Writes reports/evaluation_results.json and reports/confusion_matrix.png.
Run:  python -m machine_learning.evaluation.evaluate
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from backend.core.config import CLASS_FOLDERS, CLASS_NAMES, PROJECT_ROOT
from machine_learning.evaluation.confusion_matrix import compute_confusion_matrix, plot_confusion_matrix

REPORTS_DIR = PROJECT_ROOT / "reports"


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    labels = list(range(len(CLASS_NAMES)))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    wp, wr, wf, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
    cm = compute_confusion_matrix(y_true, y_pred)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro": {"precision": float(mp), "recall": float(mr), "f1": float(mf)},
        "weighted": {"precision": float(wp), "recall": float(wr), "f1": float(wf)},
        "per_class": {CLASS_NAMES[i]: {"precision": float(p[i]), "recall": float(r[i]),
                                       "f1": float(f[i]), "support": int(s[i])} for i in labels},
        "confusion_matrix": cm.tolist(),
        "class_order": CLASS_NAMES,
        "test_samples": int(len(y_true)),
    }


def main() -> None:
    import argparse
    import tensorflow as tf
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(PROJECT_ROOT / "dataset"))
    ap.add_argument("--model-dir", default=str(PROJECT_ROOT / "model"))
    ap.add_argument("--reports-dir", default=str(REPORTS_DIR))
    a = ap.parse_args()
    reports_dir = Path(a.reports_dir)
    model_path = Path(a.model_dir) / "poultry_mobilenetv2.h5"
    if not model_path.exists():
        raise SystemExit("Model evaluation results are not yet available (no trained model found).")
    test_dir = Path(a.data_root) / "test"
    if not any(test_dir.glob("*/*")):
        raise SystemExit("No test images found in dataset/test. Run training/preprocessing first.")
    model = tf.keras.models.load_model(model_path)
    ds = tf.keras.utils.image_dataset_from_directory(
        test_dir, label_mode="int", class_names=CLASS_FOLDERS,
        image_size=(224, 224), batch_size=32, shuffle=False)
    y_true = np.concatenate([y.numpy() for _, y in ds])
    y_pred = np.argmax(model.predict(ds), axis=1)
    results = compute_metrics(y_true, y_pred)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "evaluation_results.json").write_text(json.dumps(results, indent=2))
    plot_confusion_matrix(np.array(results["confusion_matrix"]), reports_dir / "confusion_matrix.png")
    print(json.dumps({k: results[k] for k in ("accuracy", "macro", "weighted")}, indent=2))


if __name__ == "__main__":
    main()
