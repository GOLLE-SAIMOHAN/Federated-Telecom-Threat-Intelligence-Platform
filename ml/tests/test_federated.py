import numpy as np
from flwr.common import Code, FitRes, Status, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.strategy import FedAvg

from ml.federated.simulation import (
    CLIENT_NAMES,
    FederatedClient,
    FederatedConfig,
    _metrics_from_confusion_matrix,
)


def test_default_configuration_uses_five_rounds():
    assert FederatedConfig().rounds == 5


def test_exactly_four_clients_and_local_data():
    clients = [
        FederatedClient(name, np.zeros((2, 3)), np.array([0, 1]), np.arange(2), 42)
        for name in CLIENT_NAMES
    ]
    assert tuple(client.name for client in clients) == CLIENT_NAMES
    assert all(client.features.shape == (2, 3) for client in clients)


def test_fedavg_weights_by_sample_count():
    strategy = FedAvg(inplace=False)
    first = [np.ones((2, 3)), np.ones(2)]
    second = [np.full((2, 3), 3.0), np.full(2, 3.0)]
    results = [
        (
            None,
            FitRes(
                status=Status(code=Code.OK, message=""),
                parameters=ndarrays_to_parameters(first),
                num_examples=1,
                metrics={},
            ),
        ),
        (
            None,
            FitRes(
                status=Status(code=Code.OK, message=""),
                parameters=ndarrays_to_parameters(second),
                num_examples=3,
                metrics={},
            ),
        ),
    ]
    aggregated, _ = strategy.aggregate_fit(1, results, [])
    arrays = parameters_to_ndarrays(aggregated)
    assert np.allclose(arrays[0], 2.5)
    assert np.allclose(arrays[1], 2.5)


def test_client_fit_returns_parameters_only():
    client = FederatedClient(
        "operator_a",
        np.array([[0.0, 1.0], [1.0, 0.0]]),
        np.array([0, 1]),
        np.arange(2),
        42,
    )
    updated, count, metrics = client.fit(client.get_parameters({}), {"round": 1})
    assert count == 2
    assert len(updated) == 2
    assert "features" not in metrics
    assert "labels" not in metrics
    assert "source_indices" not in metrics


def test_client_evaluates_private_local_validation_data():
    client = FederatedClient(
        "operator_a",
        np.array([[0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]),
        np.array([0, 1, 0, 1]),
        np.arange(2),
        42,
    )
    result = client.evaluate_local(client.get_parameters({}))
    assert result["validation_rows"] == 2
    assert np.asarray(result["confusion_matrix"]).shape == (2, 2)
    assert "features" not in result
    assert "labels" not in result
    assert "source_indices" not in result


def test_aggregated_confusion_matrix_metrics_are_deterministic():
    matrix = np.array([[8, 2], [1, 9]])
    metrics = _metrics_from_confusion_matrix(matrix)
    assert metrics["accuracy"] == 0.85
    assert metrics["macro_f1"] > 0.84
    assert metrics["weighted_f1"] > 0.84
