from pathlib import Path

import pytest

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

from ml.data.pipeline import (
    DatasetConfig,
    audit_train_test_overlap,
    exact_duplicate_overlap,
    inspect_train_test,
    load_dataset,
    preprocess_and_partition,
)
from ml.centralized.baseline import run_baseline


DATASET_CONFIG = Path("configs/dataset.json")


def test_dataset_config_requires_a_real_dataset_path() -> None:
    config = DatasetConfig.from_json(DATASET_CONFIG)
    assert config.dataset_path == Path("data/raw/5g-intrusion")
    assert config.label_column == "attack"


def test_missing_dataset_fails_without_creating_replacement_data(tmp_path: Path) -> None:
    missing = tmp_path / "not-present"
    with pytest.raises(FileNotFoundError, match="5G-NIDD dataset not found"):
        load_dataset(missing)
    assert not list(tmp_path.iterdir())


def test_train_test_inspection_reports_schema_and_target(tmp_path: Path) -> None:
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    train = pd.DataFrame({"feature": [1, 2, 2], "attack": ["benign", "scan", "scan"]})
    test = pd.DataFrame({"feature": [3], "attack": ["benign"]})
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)

    report = inspect_train_test(train_path, test_path, "attack")

    assert report.label_column == "attack"
    assert report.train["rows"] == 3
    assert report.test["rows"] == 1
    assert report.train["class_counts"] == {"scan": 2, "benign": 1}
    assert report.schema_compatible is True
    assert report.unsuitable_features == {}


def test_preprocessing_fits_train_only_and_partitions_reproducibly(tmp_path: Path) -> None:
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    train = pd.DataFrame(
        {
            "numeric": [None if i == 1 else float(i) for i in range(40)],
            "category": ["a", "b", None, "a"] * 10,
            "mostly_missing": [None] * 40,
            "attack": ["benign", "scan"] * 20,
        }
    )
    test = pd.DataFrame(
        {
            "numeric": [9.0, None],
            "category": ["unseen", "a"],
            "mostly_missing": [None, None],
            "attack": ["benign", "scan"],
        }
    )
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    config = DatasetConfig(
        dataset_path=tmp_path,
        train_dataset_path=train_path,
        test_dataset_path=test_path,
        label_column="attack",
        output_dir=tmp_path / "output",
        dropped_features=("mostly_missing",),
    )

    report = preprocess_and_partition(config)

    assert exact_duplicate_overlap(train, test) == 0
    assert report["preprocessing"]["feature_count"] == 3
    assert sum(report["iid"][name]["rows"] for name in ("operator_a", "operator_b", "operator_c", "operator_d")) == 40
    assert (tmp_path / "output" / "artifacts" / "preprocessing.joblib").exists()
    assert (tmp_path / "output" / "operator_partitions" / "non_iid_operator_a.npz").exists()


def test_leakage_cleanup_removes_exact_overlap_but_keeps_train_only_duplicates(
    tmp_path: Path,
) -> None:
    train = pd.DataFrame(
        {
            "feature": [1, 1, 2, 3],
            "attack": ["benign", "benign", "scan", "scan"],
        }
    )
    test = pd.DataFrame(
        {
            "feature": [1, 4],
            "attack": ["benign", "scan"],
        }
    )
    audit = audit_train_test_overlap(train, test, "attack")
    cleaned = train.loc[~pd.Series(
        [
            tuple(row) in {tuple(value) for value in test.to_numpy()}
            for row in train.to_numpy()
        ]
    )]

    assert audit["raw_train_rows"] == 4
    assert audit["unique_train_rows"] == 3
    assert audit["overlapping_train_rows"] == 2
    assert audit["neither_train_rows"] == 2
    assert audit["expected_cleaned_training_rows"] == 2
    assert audit["overlapping_test_rows"] == 1
    assert audit["unique_overlapping_records"] == 1
    assert audit["overlap_by_attack_class"] == {"benign": 2}
    assert len(cleaned) == 2
    assert exact_duplicate_overlap(cleaned, test) == 0


def test_baseline_uses_saved_artifacts_without_refitting(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    partition_dir = tmp_path / "operator_partitions"
    artifact_dir.mkdir()
    partition_dir.mkdir()
    encoder = LabelEncoder().fit(["benign", "scan"])
    import joblib

    joblib.dump({"label_encoder": encoder}, artifact_dir / "preprocessing.joblib")
    for name in ("a", "b", "c", "d"):
        np.savez(
            partition_dir / f"iid_operator_{name}.npz",
            features=np.array([[0.0, 1.0], [1.0, 0.0]]),
            labels=np.array([0, 1]),
        )
    np.savez(
        tmp_path / "test_preprocessed.npz",
        features=np.array([[0.0, 1.0], [1.0, 0.0]]),
        labels=np.array([0, 1]),
    )

    result = run_baseline(tmp_path)

    assert result["model"] == "sklearn.linear_model.SGDClassifier"
    assert result["metrics"]["accuracy"] >= 0
    assert (tmp_path / "centralized_baseline_model.joblib").exists()
