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
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


CLIENT_NAMES = ("Operator A", "Operator B", "Operator C", "Operator D")


def _classifier(classes: np.ndarray, random_state: int) -> SGDClassifier:
    model = SGDClassifier(
        loss="log_loss",
        class_weight="balanced",
        random_state=random_state,
        n_jobs=1,
    )
    model.classes_ = classes.copy()
    return model


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
        self.labels = labels
        self.classes = classes
        self.random_state = random_state

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
        model.partial_fit(self.features, self.labels, classes=self.classes)
        elapsed = time.perf_counter() - started
        return (
            [model.coef_, model.intercept_],
            len(self.labels),
            {"client": self.name, "training_time_seconds": elapsed},
        )


@dataclass(frozen=True)
class FederatedConfig:
    processed_dir: Path = Path("data/processed")
    partition_mode: str = "iid"
    rounds: int = 3
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
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision_weighted": float(
            precision_score(labels, predictions, average="weighted", zero_division=0)
        ),
        "recall_weighted": float(
            recall_score(labels, predictions, average="weighted", zero_division=0)
        ),
        "f1_weighted": float(
            f1_score(labels, predictions, average="weighted", zero_division=0)
        ),
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
    }


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
        rounds.append(
            {
                "round": round_number,
                "client_sample_counts": client_sizes,
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
        },
        "client_sizes": client_sizes,
        "rounds": rounds,
        "final_metrics": final_metrics,
    }
    output_path = processed / f"federated_{config.partition_mode}_report.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    joblib.dump(
        {
            "parameters": parameters_to_ndarrays(global_parameters),
            "classes": artifacts["label_encoder"].classes_.tolist(),
        },
        processed / f"federated_{config.partition_mode}_model.joblib",
    )
    return output


if __name__ == "__main__":
    print(json.dumps(run_federated(), indent=2))
