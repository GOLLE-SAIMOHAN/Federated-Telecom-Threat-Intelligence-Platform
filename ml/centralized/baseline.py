"""Centralized scikit-learn baseline using the leakage-free Phase 2 artifacts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)


def run_baseline(
    processed_dir: Path = Path("data/processed"),
    random_state: int = 42,
) -> dict[str, Any]:
    """Train and evaluate SGDClassifier using saved Phase 2 transformations."""
    artifacts = joblib.load(processed_dir / "artifacts" / "preprocessing.joblib")
    train_arrays = [
        np.load(processed_dir / "operator_partitions" / f"iid_operator_{name}.npz")
        for name in ("a", "b", "c", "d")
    ]
    x_train = np.concatenate([array["features"] for array in train_arrays], axis=0)
    y_train = np.concatenate([array["labels"] for array in train_arrays], axis=0)
    x_test = np.load(processed_dir / "test_preprocessed.npz")
    label_encoder = artifacts["label_encoder"]
    labels = np.arange(len(label_encoder.classes_))

    config = {
        "model": "sklearn.linear_model.SGDClassifier",
        "loss": "log_loss",
        "class_weight": "balanced",
        "random_state": random_state,
        "training_data": "data/processed/operator_partitions/iid_operator_{a,b,c,d}.npz",
        "evaluation_data": "data/processed/test_preprocessed.npz",
        "preprocessing_artifact": "data/processed/artifacts/preprocessing.joblib",
        "preprocessing_refit": False,
        "training_rows": int(len(y_train)),
        "test_rows": int(len(x_test["labels"])),
    }
    (processed_dir / "centralized_baseline_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    model = SGDClassifier(
        loss="log_loss",
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    train_started = time.perf_counter()
    model.fit(x_train, y_train)
    training_seconds = time.perf_counter() - train_started

    evaluation_started = time.perf_counter()
    predictions = model.predict(x_test["features"])
    evaluation_seconds = time.perf_counter() - evaluation_started
    y_test = x_test["labels"]
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, predictions, labels=labels, zero_division=0
    )
    results = {
        "model": config["model"],
        "training_time_seconds": training_seconds,
        "evaluation_time_seconds": evaluation_seconds,
        "metrics": {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(precision_score(y_test, predictions, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_test, predictions, average="weighted", zero_division=0)),
            "f1": float(f1_score(y_test, predictions, average="weighted", zero_division=0)),
            "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(y_test, predictions, average="weighted", zero_division=0)),
        },
        "per_class": {
            str(label_encoder.classes_[index]): {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index in labels
        },
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "class_mapping": {
            str(label): int(index)
            for index, label in enumerate(label_encoder.classes_)
        },
    }
    joblib.dump(model, processed_dir / "centralized_baseline_model.joblib")
    (processed_dir / "centralized_baseline_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results


if __name__ == "__main__":
    print(json.dumps(run_baseline(), indent=2))
