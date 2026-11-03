"""Inference for the saved five-round federated global model."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier


MODEL_VERSION = "federated_iid_rounds_5"
DEFAULT_PROCESSED_DIR = Path("data/processed")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_LOADED_ESTIMATOR: SGDClassifier | None = None
_LOADED_ARTIFACTS: dict[str, Any] | None = None


class InferenceValidationError(ValueError):
    """Raised when an uploaded traffic table does not match the model schema."""


def resolve_artifact_directory(processed_dir: Path | None = None) -> Path:
    configured = os.environ.get("INFERENCE_ARTIFACT_DIR")
    directory = Path(configured) if configured else (processed_dir or REPOSITORY_ROOT / "data" / "processed")
    return directory if directory.is_absolute() else REPOSITORY_ROOT / directory


def load_federated_estimator(processed_dir: Path | None = None) -> tuple[SGDClassifier, dict[str, Any]]:
    """Reconstruct the estimator from Flower's serialized parameter arrays."""
    artifact_directory = resolve_artifact_directory(processed_dir)
    model_path = artifact_directory / f"{MODEL_VERSION}_model.joblib"
    preprocessing_path = (
        artifact_directory / "preprocessing.joblib"
        if os.environ.get("INFERENCE_ARTIFACT_DIR")
        else artifact_directory / "artifacts" / "preprocessing.joblib"
    )
    if os.environ.get("INFERENCE_ARTIFACT_DIR") is None and processed_dir is None:
        preprocessing_path = REPOSITORY_ROOT / "data" / "processed" / "artifacts" / "preprocessing.joblib"
    model_bundle = joblib.load(model_path)
    artifacts = joblib.load(preprocessing_path)
    classes = np.asarray(model_bundle["classes"])
    parameters = model_bundle["parameters"]
    if len(parameters) != 2 or parameters[0].shape[0] != len(classes):
        raise RuntimeError("The federated model parameter bundle is incompatible with its classes.")
    estimator = SGDClassifier(loss="log_loss", class_weight=None, random_state=42, n_jobs=1)
    estimator.classes_ = classes.copy()
    estimator.coef_ = np.asarray(parameters[0], dtype=np.float64).copy()
    estimator.intercept_ = np.asarray(parameters[1], dtype=np.float64).copy()
    estimator.n_features_in_ = estimator.coef_.shape[1]
    estimator.n_iter_ = 1
    estimator.t_ = 1.0
    if estimator.coef_.shape[1] != len(artifacts["preprocessor"].get_feature_names_out()):
        raise RuntimeError("The model and preprocessing artifacts have incompatible feature dimensions.")
    return estimator, artifacts


def initialize_inference(processed_dir: Path | None = None) -> None:
    global _LOADED_ESTIMATOR, _LOADED_ARTIFACTS
    _LOADED_ESTIMATOR, _LOADED_ARTIFACTS = load_federated_estimator(processed_dir)


def _validate_and_transform(
    frame: pd.DataFrame, artifacts: dict[str, Any]
) -> tuple[np.ndarray, list[str]]:
    if frame.empty:
        raise InferenceValidationError("The CSV must contain at least one data row.")
    if frame.columns.empty or not frame.columns.is_unique:
        raise InferenceValidationError("The CSV must have unique, non-empty column names.")
    feature_columns = list(artifacts["feature_columns"])
    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise InferenceValidationError(f"Missing required feature columns: {', '.join(missing)}")
    features = frame[feature_columns].copy()
    numeric_columns = set(artifacts["preprocessor"].transformers_[0][2])
    for column in numeric_columns:
        converted = pd.to_numeric(features[column], errors="coerce")
        invalid = features[column].notna() & converted.isna()
        if invalid.any():
            raise InferenceValidationError(f"Column '{column}' contains non-numeric values.")
        features[column] = converted
    transformed = artifacts["preprocessor"].transform(features)
    return np.asarray(transformed, dtype=np.float64), feature_columns


def predict_frame(
    frame: pd.DataFrame, processed_dir: Path = DEFAULT_PROCESSED_DIR
) -> dict[str, Any]:
    estimator = _LOADED_ESTIMATOR
    artifacts = _LOADED_ARTIFACTS
    if estimator is None or artifacts is None:
        estimator, artifacts = load_federated_estimator(processed_dir)
    transformed, feature_columns = _validate_and_transform(frame, artifacts)
    if len(frame) == 0:
        raise InferenceValidationError("The CSV must contain at least one data row.")
    numeric_predictions = estimator.predict(transformed)
    probabilities = estimator.predict_proba(transformed)
    classes = [str(value) for value in estimator.classes_]
    predictions: list[dict[str, Any]] = []
    attack_events: list[dict[str, Any]] = []
    attack_classes = {"benign"}
    metadata_columns = [
        column for column in frame.columns
        if column not in feature_columns and column != "attack"
        and any(token in column.lower() for token in ("ip", "port", "flow", "time", "protocol"))
    ]
    for index, (numeric_class, row_probabilities) in enumerate(
        zip(numeric_predictions, probabilities)
    ):
        predicted_class = str(numeric_class)
        score = float(np.max(row_probabilities))
        record = {
            "row_number": index + 2,
            "predicted_class": predicted_class,
            "model_score": score,
            "probabilities": {
                classes[position]: float(value)
                for position, value in enumerate(row_probabilities)
            },
        }
        for column in metadata_columns:
            value = frame.iloc[index][column]
            if pd.notna(value):
                record[column] = value.item() if hasattr(value, "item") else value
        predictions.append(record)
        if predicted_class not in attack_classes:
            attack_events.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "predicted_attack_category": predicted_class,
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "model_version": MODEL_VERSION,
                    "model_score": score,
                    "flow_metadata": {column: record[column] for column in metadata_columns if column in record},
                }
            )
    counts = pd.Series([item["predicted_class"] for item in predictions]).value_counts()
    return {
        "model_version": MODEL_VERSION,
        "processed_rows": len(predictions),
        "predictions": predictions,
        "summary": [
            {"predicted_class": str(label), "count": int(count)}
            for label, count in counts.items()
        ],
        "attack_events": attack_events,
        "benign_count": sum(item["predicted_class"] == "benign" for item in predictions),
        "attack_count": len(attack_events),
    }


def predict_csv(csv_text: str, processed_dir: Path = DEFAULT_PROCESSED_DIR) -> dict[str, Any]:
    try:
        frame = pd.read_csv(io.StringIO(csv_text))
    except Exception as error:
        raise InferenceValidationError("The uploaded file is not a valid CSV.") from error
    max_rows = min(int(os.environ.get("DETECTION_MAX_ROWS", "10000")), 10000)
    if len(frame) > max_rows:
        raise InferenceValidationError("The CSV exceeds the maximum row limit.")
    return predict_frame(frame, processed_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    args = parser.parse_args()
    try:
        result = predict_csv(sys.stdin.read(), args.processed_dir)
    except (InferenceValidationError, FileNotFoundError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
