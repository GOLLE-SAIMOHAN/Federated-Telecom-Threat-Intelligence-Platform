"""Four-client Flower federated simulation for the existing SGD baseline."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from flwr.client import NumPyClient
from flwr.common import (
    Code,
    FitRes,
    Parameters,
    Status,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.strategy import FedAvg
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight


CLIENT_NAMES = ("Operator A", "Operator B", "Operator C", "Operator D")


def _classifier(classes: np.ndarray, random_state: int) -> SGDClassifier:
    model = SGDClassifier(
        loss="log_loss",
        class_weight=None,
        random_state=random_state,
        n_jobs=1,
    )
    model.classes_ = classes.copy()
    return model


def _local_train_validation_split(
    features: np.ndarray,
    labels: np.ndarray,
    classes: np.ndarray,
    random_state: int,
    validation_fraction: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create a deterministic per-class split without sharing validation arrays."""
    rng = np.random.default_rng(random_state)
    train_indices: list[int] = []
    validation_indices: list[int] = []
    for label in classes:
        indices = np.flatnonzero(labels == label)
        rng.shuffle(indices)
        validation_count = min(
            max(1, int(len(indices) * validation_fraction)),
            max(0, len(indices) - 1),
        )
        validation_indices.extend(indices[:validation_count].tolist())
        train_indices.extend(indices[validation_count:].tolist())
    return (
        features[train_indices],
        labels[train_indices],
        features[validation_indices],
        labels[validation_indices],
    )


def _metrics_from_confusion_matrix(matrix: np.ndarray) -> dict[str, float]:
    """Calculate global classification metrics from aggregated count data."""
    matrix = np.asarray(matrix, dtype=np.int64)
    total = int(matrix.sum())
    if total == 0:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
        }
    true_positive = np.diag(matrix).astype(np.float64)
    actual = matrix.sum(axis=1).astype(np.float64)
    predicted = matrix.sum(axis=0).astype(np.float64)
    precision = np.divide(true_positive, predicted, out=np.zeros_like(true_positive), where=predicted != 0)
    recall = np.divide(true_positive, actual, out=np.zeros_like(true_positive), where=actual != 0)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(true_positive),
        where=(precision + recall) != 0,
    )
    return {
        "accuracy": float(true_positive.sum() / total),
        "precision": float(np.average(precision, weights=actual)),
        "recall": float(np.average(recall, weights=actual)),
        "macro_f1": float(f1.mean()),
        "weighted_f1": float(np.average(f1, weights=actual)),
    }


class FederatedClient(NumPyClient):
    """A client that owns only one operator's transformed local arrays."""

    def __init__(
        self,
        name: str,
        features: np.ndarray,
        labels: np.ndarray,
        classes: np.ndarray,
        random_state: int,
    ) -> None:
        self.name = name
        self.features = np.asarray(features, dtype=np.float64)
        self.labels = np.asarray(labels)
        self.classes = np.asarray(classes)
        self.random_state = random_state
        (
            self.train_features,
            self.train_labels,
            self.validation_features,
            self.validation_labels,
        ) = _local_train_validation_split(
            self.features,
            self.labels,
            self.classes,
            random_state,
        )

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        feature_count = self.features.shape[1]
        return [
            np.zeros((len(self.classes), feature_count), dtype=np.float64),
            np.zeros(len(self.classes), dtype=np.float64),
        ]

    def fit(
        self, parameters: list[np.ndarray], config: dict[str, Any]
    ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        model = _classifier(self.classes, self.random_state + int(config["round"]))
        model.coef_ = np.asarray(parameters[0], dtype=np.float64).copy()
        model.intercept_ = np.asarray(parameters[1], dtype=np.float64).copy()
        model.n_features_in_ = self.features.shape[1]
        model.n_iter_ = 0
        model.t_ = 1.0
        started = time.perf_counter()
        model.partial_fit(
            self.train_features,
            self.train_labels,
            classes=self.classes,
            sample_weight=compute_sample_weight("balanced", self.train_labels),
        )
        elapsed = time.perf_counter() - started
        return (
            [model.coef_, model.intercept_],
            len(self.train_labels),
            {"client": self.name, "training_time_seconds": elapsed},
        )

    def evaluate_local(self, parameters: list[np.ndarray]) -> dict[str, Any]:
        """Evaluate global parameters on this client's private validation split."""
        model = _classifier(self.classes, 0)
        model.coef_ = np.asarray(parameters[0], dtype=np.float64)
        model.intercept_ = np.asarray(parameters[1], dtype=np.float64)
        model.n_features_in_ = self.validation_features.shape[1]
        predictions = model.predict(self.validation_features)
        return {
            "client": self.name,
            "validation_rows": int(len(self.validation_labels)),
            "confusion_matrix": confusion_matrix(
                self.validation_labels,
                predictions,
                labels=self.classes,
            ).tolist(),
        }

@dataclass(frozen=True)
class FederatedConfig:
    processed_dir: Path = Path("data/processed")
    partition_mode: str = "iid"
    rounds: int = 5
    random_state: int = 42


def _evaluate(
    parameters: list[np.ndarray],
    features: np.ndarray,
    labels: np.ndarray,
    classes: np.ndarray,
) -> dict[str, float]:
    model = _classifier(classes, 0)
    model.coef_ = parameters[0]
    model.intercept_ = parameters[1]
    model.n_features_in_ = features.shape[1]
    predictions = model.predict(features)
    return _metrics_from_confusion_matrix(
        confusion_matrix(labels, predictions, labels=classes)
    )


def run_federated(config: FederatedConfig = FederatedConfig()) -> dict[str, Any]:
    if config.partition_mode not in {"iid", "non_iid"}:
        raise ValueError("partition_mode must be 'iid' or 'non_iid'.")
    if config.rounds < 1:
        raise ValueError("rounds must be at least one.")
    processed = config.processed_dir
    artifacts = joblib.load(processed / "artifacts" / "preprocessing.joblib")
    classes = np.arange(len(artifacts["label_encoder"].classes_))
    clients: list[FederatedClient] = []
    client_sizes: dict[str, int] = {}
    for index, name in enumerate(CLIENT_NAMES):
        stem = f"operator_{chr(ord('a') + index)}"
        data = np.load(
            processed / "operator_partitions" / f"{config.partition_mode}_{stem}.npz"
        )
        clients.append(
            FederatedClient(
                name,
                data["features"],
                data["labels"],
                classes,
                config.random_state,
            )
        )
        client_sizes[name] = int(len(data["labels"]))

    strategy = FedAvg(inplace=False)
    global_parameters = ndarrays_to_parameters(clients[0].get_parameters({}))
    rounds: list[dict[str, Any]] = []
    for round_number in range(1, config.rounds + 1):
        fit_results: list[tuple[None, FitRes]] = []
        round_started = time.perf_counter()
        for client in clients:
            updated, count, metrics = client.fit(
                parameters_to_ndarrays(global_parameters),
                {"round": round_number},
            )
            fit_results.append(
                (
                    None,
                    FitRes(
                        status=Status(code=Code.OK, message=""),
                        parameters=ndarrays_to_parameters(updated),
                        num_examples=count,
                        metrics=metrics,
                    ),
                )
            )
        global_parameters, _ = strategy.aggregate_fit(round_number, fit_results, [])
        if global_parameters is None:
            raise RuntimeError("Flower FedAvg returned no global parameters.")
        update_arrays = parameters_to_ndarrays(global_parameters)
        validation_matrix = np.zeros((len(classes), len(classes)), dtype=np.int64)
        validation_rows = 0
        for client in clients:
            validation = client.evaluate_local(update_arrays)
            validation_matrix += np.asarray(validation["confusion_matrix"], dtype=np.int64)
            validation_rows += int(validation["validation_rows"])
        rounds.append(
            {
                "round": round_number,
                "client_sample_counts": client_sizes,
                "validation_rows": validation_rows,
                "validation_metrics": _metrics_from_confusion_matrix(validation_matrix),
                "validation_confusion_matrix": validation_matrix.tolist(),
                "training_time_seconds": time.perf_counter() - round_started,
                "model_update": {
                    "parameter_names": ["coef_", "intercept_"],
                    "parameter_bytes": int(sum(array.nbytes for array in update_arrays)),
                    "aggregation": "Flower FedAvg weighted by client sample count",
                },
            }
        )

    test = np.load(processed / "test_preprocessed.npz")
    final_metrics = _evaluate(
        parameters_to_ndarrays(global_parameters),
        test["features"],
        test["labels"],
        classes,
    )
    output = {
        "configuration": {
            "framework": "Flower",
            "clients": list(CLIENT_NAMES),
            "partition_mode": config.partition_mode,
            "rounds": config.rounds,
            "random_state": config.random_state,
            "model": "sklearn.linear_model.SGDClassifier",
            "loss": "log_loss",
            "preprocessing_refit": False,
            "server_receives_raw_data": False,
            "validation_strategy": "deterministic per-operator local validation split",
        },
        "client_sizes": client_sizes,
        "rounds": rounds,
        "final_metrics": final_metrics,
    }
    output_path = processed / f"federated_{config.partition_mode}_rounds_{config.rounds}_report.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    joblib.dump(
        {
            "parameters": parameters_to_ndarrays(global_parameters),
            "classes": artifacts["label_encoder"].classes_.tolist(),
        },
        processed / f"federated_{config.partition_mode}_rounds_{config.rounds}_model.joblib",
    )
    return output


if __name__ == "__main__":
    print(json.dumps(run_federated(), indent=2))
