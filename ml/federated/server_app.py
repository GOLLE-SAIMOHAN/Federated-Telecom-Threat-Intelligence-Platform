"""Network-connected Flower server for the first local deployment proof."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from flwr.common import ndarrays_to_parameters
from flwr.common import Context
from flwr.server import ServerApp, ServerAppComponents, ServerConfig
from flwr.server.strategy import FedAvg


def _proof_path() -> Path:
    return Path(
        os.environ.get(
            "FLOWER_NETWORK_PROOF_RESULTS",
            "data/processed/network_proof_results.json",
        )
    )


def _aggregate_fit_metrics(
    results: list[tuple[int, dict[str, Any]]],
) -> dict[str, Any]:
    total_examples = sum(num_examples for num_examples, _ in results)
    training_time = (
        sum(float(metrics.get("training_time_seconds", 0.0)) for _, metrics in results)
        / len(results)
        if results
        else 0.0
    )
    record = {
        "round": 1,
        "connected_clients": len(results),
        "client_examples": total_examples,
        "average_training_time_seconds": training_time,
        "clients": [metrics.get("client", "unknown") for _, metrics in results],
    }
    output_path = _proof_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {
        "client_count": len(results),
        "client_examples": total_examples,
        "average_training_time_seconds": training_time,
    }


def server_fn(context: Context) -> ServerAppComponents:
    processed_dir = Path(
        str(context.run_config.get("processed-dir", "data/processed"))
    )
    artifacts = joblib.load(processed_dir / "artifacts" / "preprocessing.joblib")
    classes = len(artifacts["label_encoder"].classes_)
    features = len(artifacts["preprocessor"].get_feature_names_out())
    initial_parameters = ndarrays_to_parameters(
        [
            np.zeros((classes, features), dtype=np.float64),
            np.zeros(classes, dtype=np.float64),
        ]
    )
    strategy = FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=4,
        min_evaluate_clients=4,
        min_available_clients=4,
        initial_parameters=initial_parameters,
        fit_metrics_aggregation_fn=_aggregate_fit_metrics,
    )
    return ServerAppComponents(
        strategy=strategy,
        config=ServerConfig(num_rounds=1),
    )


app = ServerApp(server_fn=server_fn)
