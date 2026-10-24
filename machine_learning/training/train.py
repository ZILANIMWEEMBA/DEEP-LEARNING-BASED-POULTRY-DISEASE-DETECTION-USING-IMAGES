"""Train the MobileNetV2 poultry-disease classifier (transfer learning).

Usage:
    python -m machine_learning.training.train --epochs 15 --fine-tune-epochs 10

Requires images in dataset/raw/<class>/ (see README "Dataset Setup").
Nothing is fabricated: metadata is written only from the real training run.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import CLASS_FOLDERS, CLASS_NAMES, PROJECT_ROOT
from machine_learning.preprocessing.preprocess import IMG_SIZE, SEED, split_dataset, validate_dataset

MODEL_DIR = PROJECT_ROOT / "model"
REPORTS_DIR = PROJECT_ROOT / "reports"


def compute_class_weights(counts: dict[str, int], class_names: list[str] | None = None,
                         healthy_priority: float = 1.0) -> dict[int, float]:
    """Return inverse-frequency weights for each class index.

    Balanced datasets keep equal weights; a healthy_priority > 1.0 increases the
    importance of the Healthy class so healthy flocks are not penalised when the
    model is learning from a small or imperfect dataset.
    """
    names = class_names or CLASS_NAMES
    values = [max(int(counts.get(name, 0)), 1) for name in names]
    if not values:
        return {0: 1.0}
    baseline = [1.0 / v for v in values]
    if healthy_priority != 1.0:
        baseline[0] *= healthy_priority
    max_v = max(baseline) or 1.0
    return {idx: float(v / max_v) for idx, v in enumerate(baseline)}


def load_split(root: Path, split: str, batch: int, shuffle: bool):
    import tensorflow as tf
    # class_names=CLASS_FOLDERS pins the label order (never rely on alphabetical order)
    return tf.keras.utils.image_dataset_from_directory(
        root / split, labels="inferred", label_mode="int", class_names=CLASS_FOLDERS,
        image_size=(IMG_SIZE, IMG_SIZE), batch_size=batch, shuffle=shuffle, seed=SEED)


def build_model(dropout: float = 0.3, weights: str | None = "imagenet"):
    import tensorflow as tf
    from tensorflow.keras import layers

    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights=weights)
    base.trainable = False  # stage 1: frozen backbone
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = layers.Rescaling(1 / 127.5, offset=-1)(inputs)      # MobileNetV2 normalisation
    x = base(x, training=False)                               # 7x7x1280 feature map
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(len(CLASS_NAMES), activation="softmax")(x)
    return tf.keras.Model(inputs, outputs, name="poultry_mobilenetv2"), base


def augmentation():
    """Mild, clinically-safe augmentation. Applied to the TRAINING set only."""
    from tensorflow.keras import layers
    import tensorflow as tf
    return tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.05),
        layers.RandomZoom(0.1),
        layers.RandomTranslation(0.05, 0.05),
        layers.RandomBrightness(0.1, value_range=(0, 255)),
    ], name="augmentation")


def build_loss(label_smoothing: float = 0.05):
    """Compatibility wrapper for TensorFlow versions that do not accept label_smoothing."""
    import tensorflow as tf
    try:
        return tf.keras.losses.SparseCategoricalCrossentropy(label_smoothing=label_smoothing)
    except TypeError:
        return tf.keras.losses.SparseCategoricalCrossentropy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--fine-tune-epochs", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--fine-tune-lr", type=float, default=1e-5)
    ap.add_argument("--unfreeze-layers", type=int, default=30)
    ap.add_argument("--raw", default=str(PROJECT_ROOT / "dataset" / "raw"))
    ap.add_argument("--data-root", default=str(PROJECT_ROOT / "dataset"), help="folder holding train/validation/test")
    ap.add_argument("--model-dir", default=str(MODEL_DIR))
    ap.add_argument("--reports-dir", default=str(REPORTS_DIR))
    ap.add_argument("--weights", default="imagenet", choices=["imagenet", "none"],
                    help="'none' is for offline pipeline smoke tests only")
    ap.add_argument("--healthy-priority", type=float, default=3.0,
                    help="Boost the Healthy class weight more strongly so healthy birds remain the dominant class when confidence is high.")
    ap.add_argument("--skip-split", action="store_true", help="reuse existing dataset/train|validation|test")
    a = ap.parse_args()

    import tensorflow as tf
    tf.keras.utils.set_random_seed(SEED)
    data_root = Path(a.data_root)
    model_dir, reports_dir = Path(a.model_dir), Path(a.reports_dir)

    # 1-3. validate + split
    if not a.skip_split:
        report = validate_dataset(Path(a.raw))
        if report["total_valid"] == 0:
            raise SystemExit("No images found in dataset/raw/<class>/. See README 'Dataset Setup'.")
        print("Dataset validation:", json.dumps({k: report[k] for k in ("classes", "total_valid", "imbalance_ratio")}))
        print("Unreadable:", len(report["unreadable"]), "Duplicates:", len(report["duplicates"]))
        counts = split_dataset(Path(a.raw), data_root)
    else:
        counts = None

    train_ds = load_split(data_root, "train", a.batch_size, True)
    val_ds = load_split(data_root, "validation", a.batch_size, False)
    train_counts = {name: int(sum(1 for _ in (data_root / "train" / folder).glob("*"))) for name, folder in zip(CLASS_NAMES, CLASS_FOLDERS)}
    class_weights = compute_class_weights(train_counts, CLASS_NAMES, healthy_priority=a.healthy_priority)
    n_train = int(train_ds.cardinality().numpy()) * a.batch_size
    aug = augmentation()
    train_ds = train_ds.map(lambda x, y: (aug(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)

    # 4-6. model
    model, base = build_model(weights=None if a.weights == "none" else "imagenet")
    model_dir.mkdir(parents=True, exist_ok=True); reports_dir.mkdir(parents=True, exist_ok=True)
    ckpt = model_dir / "poultry_mobilenetv2.h5"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(str(ckpt), monitor="val_accuracy", save_best_only=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-7),
    ]
    model.compile(optimizer=tf.keras.optimizers.Adam(a.lr),
                  loss=build_loss(0.05),
                  metrics=["accuracy"])
    print("Class weights:", {CLASS_NAMES[i]: w for i, w in class_weights.items()})
    h1 = model.fit(train_ds, validation_data=val_ds, epochs=a.epochs, callbacks=callbacks,
                   class_weight=class_weights, verbose=2)
    history = {k: [float(v) for v in vs] for k, vs in h1.history.items()}
    total_epochs = len(h1.history["loss"])

    # 7. optional fine-tuning of upper layers at a low learning rate
    if a.fine_tune_epochs > 0:
        base.trainable = True
        for layer in base.layers[:-a.unfreeze_layers]:
            layer.trainable = False
        model.compile(optimizer=tf.keras.optimizers.Adam(a.fine_tune_lr),
                      loss=build_loss(0.05),
                      metrics=["accuracy"])
        h2 = model.fit(train_ds, validation_data=val_ds, epochs=a.fine_tune_epochs, callbacks=callbacks,
                       class_weight=class_weights, verbose=2)
        for k, vs in h2.history.items():
            history.setdefault(k, []).extend(float(v) for v in vs)
        total_epochs += len(h2.history["loss"])

    # best checkpoint (by val accuracy) is on disk; reload it as the final model
    model = tf.keras.models.load_model(ckpt)
    val_loss, val_acc = model.evaluate(val_ds, verbose=0)

    # 8. persist class mapping + metadata (real values only)
    (model_dir / "class_names.json").write_text(json.dumps(CLASS_NAMES, indent=2))
    if counts is None:
        counts = {s: {f: len(list((data_root / s / f).glob("*"))) for f in CLASS_FOLDERS}
                  for s in ("train", "validation", "test")}
    sizes = {s: sum(c.values()) for s, c in counts.items()}
    metadata = {
        "model": "MobileNetV2",
        "pretrained_weights": a.weights,
        "input_size": [IMG_SIZE, IMG_SIZE, 3],
        "classes": CLASS_NAMES,
        "framework": f"TensorFlow/Keras {tf.__version__}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "dataset_size": sum(sizes.values()),
        "training_samples": sizes["train"],
        "validation_samples": sizes["validation"],
        "test_samples": sizes["test"],
        "num_classes": len(CLASS_NAMES),
        "training_epochs": total_epochs,
        "fine_tune_epochs": a.fine_tune_epochs,
        "best_validation_accuracy": float(max(history.get("val_accuracy", [val_acc]))),
        "final_validation_accuracy": float(val_acc),
        "normalisation": "Rescaling(1/127.5, offset=-1) inside the model; input is RGB 0-255",
        "version": datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S"),
    }
    (model_dir / "model_metadata.json").write_text(json.dumps(metadata, indent=2))
    (reports_dir / "training_history.json").write_text(json.dumps(history, indent=2))
    print("Saved:", ckpt)
    print("Next: python -m machine_learning.evaluation.evaluate")


if __name__ == "__main__":
    main()
