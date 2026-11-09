"""Network-connected Flower client for the first local deployment proof."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from flwr.client import ClientApp
from flwr.common import Context

from ml.federated.simulation import FederatedClient


class NetworkFederatedClient(FederatedClient):
    """Adapt the existing local client to Flower's network message config."""

    def fit(
        self, parameters: list[np.ndarray], config: dict[str, Any]
    ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        return super().fit(parameters, {"round": int(config.get("server_round", 1))})

    def evaluate(
        self, parameters: list[np.ndarray], config: dict[str, Any]
    ) -> tuple[float, int, dict[str, Any]]:
        validation = self.evaluate_local(parameters)
        matrix = np.asarray(validation["confusion_matrix"], dtype=np.float64)
        rows = int(validation["validation_rows"])
        accuracy = float(np.trace(matrix) / rows) if rows else 0.0
        return 0.0, rows, {
            "accuracy": accuracy,
            "validation_rows": rows,
        }


def client_fn(context: Context):
    processed_dir = Path(
        str(context.run_config.get("processed-dir", "data/processed"))
    )
    partition_mode = str(context.run_config.get("partition-mode", "iid"))
    partition_id = int(context.node_config.get("partition-id", 0))
    if partition_id not in range(4):
        raise ValueError("The local network proof supports partition IDs 0 through 3.")
    operator_name = f"Operator {chr(ord('A') + partition_id)}"
    operator_stem = f"operator_{chr(ord('a') + partition_id)}"

    artifacts = joblib.load(processed_dir / "artifacts" / "preprocessing.joblib")
    data = np.load(
        processed_dir
        / "operator_partitions"
        / f"{partition_mode}_{operator_stem}.npz"
    )
    classes = np.arange(len(artifacts["label_encoder"].classes_))
    return NetworkFederatedClient(
        operator_name,
        data["features"],
        data["labels"],
        classes,
        random_state=int(context.run_config.get("random-state", 42)),
    ).to_client()


app = ClientApp(client_fn=client_fn)
