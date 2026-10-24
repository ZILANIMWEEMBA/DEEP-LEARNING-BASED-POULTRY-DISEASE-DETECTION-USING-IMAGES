"""4x4 confusion matrix plotting."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import seaborn as sns  # noqa: E402
from sklearn.metrics import confusion_matrix  # noqa: E402

from backend.core.config import CLASS_NAMES  # noqa: E402


def compute_confusion_matrix(y_true, y_pred) -> np.ndarray:
    return confusion_matrix(y_true, y_pred, labels=list(range(len(CLASS_NAMES))))


def plot_confusion_matrix(cm: np.ndarray, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=CLASS_NAMES,
                yticklabels=CLASS_NAMES, ax=ax)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title("Confusion Matrix (test set)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
