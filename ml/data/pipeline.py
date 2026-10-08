"""Reusable, structure-agnostic pipeline for the 5G-NIDD dataset.

This module deliberately does not assume a dataset column name. The label
column must be supplied after inspecting the downloaded dataset.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler


OPERATOR_NAMES = ("operator_a", "operator_b", "operator_c", "operator_d")


@dataclass(frozen=True)
class DatasetConfig:
    dataset_path: Path
    train_dataset_path: Path | None = None
    test_dataset_path: Path | None = None
    label_column: str | None = None
    test_size: float = 0.2
    random_seed: int = 42
    partition_mode: str = "iid"
    non_iid_concentration: float = 0.5
    output_dir: Path = Path("data/processed")
    dropped_features: tuple[str, ...] = (
        "ip.fragments",
        "tcp.segments",
        "tcp.reassembled.length",
        "udp.port",
        "udp.length",
    )

    @classmethod
    def from_json(cls, path: Path) -> "DatasetConfig":
        values = json.loads(path.read_text(encoding="utf-8"))
        values["dataset_path"] = Path(values["dataset_path"])
        if values.get("train_dataset_path") is not None:
            values["train_dataset_path"] = Path(values["train_dataset_path"])
        if values.get("test_dataset_path") is not None:
            values["test_dataset_path"] = Path(values["test_dataset_path"])
        values["output_dir"] = Path(values.get("output_dir", "data/processed"))
        return cls(**values)

    def validate(self) -> None:
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if self.partition_mode not in {"iid", "non_iid"}:
            raise ValueError("partition_mode must be either 'iid' or 'non_iid'.")
        if self.non_iid_concentration <= 0:
            raise ValueError("non_iid_concentration must be greater than zero.")


@dataclass(frozen=True)
class DatasetInspection:
    dataset_path: str
    rows: int
    columns: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_rows: int
    label_column: str
    label_distribution: dict[str, int]
    feature_columns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatasetPairInspection:
    label_column: str
    train: dict[str, Any]
    test: dict[str, Any]
    schema_compatible: bool
    schema_differences: list[str]
    unsuitable_features: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedDataset:
    features: np.ndarray
    labels: np.ndarray
    label_classes: list[str]
    feature_names: list[str]
    label_encoder: LabelEncoder
    preprocessor: ColumnTransformer


@dataclass(frozen=True)
class DatasetSplit:
    x_train: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    train_indices: np.ndarray
    test_indices: np.ndarray


@dataclass(frozen=True)
class OperatorPartition:
    name: str
    x_train: np.ndarray
    y_train: np.ndarray
    source_indices: np.ndarray


def load_dataset(path: Path) -> pd.DataFrame:
    """Load a supported tabular file without changing its contents."""
    if not path.exists():
        raise FileNotFoundError(
            f"5G-NIDD dataset not found at '{path}'. "
            "Place the downloaded dataset under data/raw/5g-nidd and configure dataset_path."
        )
    if path.is_dir():
        candidates = sorted(
            file
            for pattern in ("*.csv", "*.parquet", "*.xlsx", "*.xls")
            for file in path.glob(pattern)
        )
        if not candidates:
            raise ValueError(f"No supported dataset files were found in '{path}'.")
        frames = [load_dataset(candidate) for candidate in candidates]
        columns = frames[0].columns
        if any(not frame.columns.equals(columns) for frame in frames[1:]):
            raise ValueError("Dataset files in the directory do not have matching columns.")
        return pd.concat(frames, ignore_index=True)

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported dataset format '{suffix}'. Use CSV, Parquet, or Excel.")


def inspect_dataset(frame: pd.DataFrame, dataset_path: Path, label_column: str | None) -> DatasetInspection:
    """Validate basic tabular structure and report observed dataset facts."""
    if frame.empty:
        raise ValueError("The dataset contains no rows.")
    if frame.columns.empty or not frame.columns.is_unique:
        raise ValueError("The dataset must have unique, non-empty column names.")
    if label_column is None:
        raise ValueError(
            "label_column is required. Inspect the reported columns and set the actual label column."
        )
    if label_column not in frame.columns:
        raise ValueError(
            f"Configured label column '{label_column}' was not found. "
            f"Observed columns: {list(frame.columns)}"
        )
    if frame[label_column].isna().all():
        raise ValueError(f"Label column '{label_column}' contains only missing values.")

    distribution = frame[label_column].value_counts(dropna=False)
    return DatasetInspection(
        dataset_path=str(dataset_path),
        rows=len(frame),
        columns=[str(column) for column in frame.columns],
        dtypes={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        missing_values={str(column): int(value) for column, value in frame.isna().sum().items()},
        duplicate_rows=int(frame.duplicated().sum()),
        label_column=label_column,
        label_distribution={str(label): int(count) for label, count in distribution.items()},
        feature_columns=[str(column) for column in frame.columns if column != label_column],
    )


def _inspect_frame(frame: pd.DataFrame, label_column: str) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("The dataset contains no rows.")
    if frame.columns.empty or not frame.columns.is_unique:
        raise ValueError("The dataset must have unique, non-empty column names.")
    if label_column not in frame.columns:
        raise ValueError(f"Configured label column '{label_column}' was not found.")
    distribution = frame[label_column].value_counts(dropna=False)
    return {
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": {
            str(column): int(value) for column, value in frame.isna().sum().items()
        },
        "duplicate_rows": int(frame.duplicated().sum()),
        "class_counts": {str(label): int(count) for label, count in distribution.items()},
    }


def inspect_train_test(
    train_path: Path,
    test_path: Path,
    label_column: str | None = None,
) -> DatasetPairInspection:
    """Inspect the real train/test files without transforming or partitioning them."""
    train = load_dataset(train_path)
    test = load_dataset(test_path)
    if label_column is None:
        candidates = ("attack", "label", "target", "class")
        shared = [column for column in candidates if column in train.columns and column in test.columns]
        if len(shared) != 1:
            raise ValueError(
                "label_column must be configured when a unique conventional label "
                "column cannot be identified."
            )
        label_column = shared[0]
    train_report = _inspect_frame(train, label_column)
    test_report = _inspect_frame(test, label_column)
    differences: list[str] = []
    if train_report["columns"] != test_report["columns"]:
        differences.append("Column names or order differ between train and test.")
    if train_report["dtypes"] != test_report["dtypes"]:
        differences.append("Column dtypes differ between train and test.")

    unsuitable: dict[str, str] = {}
    for column in train_report["columns"]:
        if column == label_column:
            continue
        missing_ratio = train_report["missing_values"][column] / train_report["rows"]
        if missing_ratio >= 0.95:
            unsuitable[column] = (
                f"{missing_ratio:.2%} of training values are missing; unsuitable "
                "as a raw feature without a justified missingness strategy."
            )
        elif train_report["dtypes"][column] == "object":
            unique_ratio = train[column].nunique(dropna=True) / max(len(train), 1)
            if unique_ratio > 0.5:
                unsuitable[column] = (
                    "High-cardinality text/categorical values are unsuitable as raw "
                    "numeric features and require explicit encoding or feature extraction."
                )

    return DatasetPairInspection(
        label_column=label_column,
        train=train_report,
        test=test_report,
        schema_compatible=not differences,
        schema_differences=differences,
        unsuitable_features=unsuitable,
    )


def exact_duplicate_overlap(train: pd.DataFrame, test: pd.DataFrame) -> int:
    """Return exact test-row overlap count using every supplied column."""
    return int(_exact_overlap_mask(test, train).sum())


def _exact_overlap_mask(source: pd.DataFrame, reference: pd.DataFrame) -> np.ndarray:
    """Match complete rows, treating missing values in the same position as equal."""
    source_hashes = pd.util.hash_pandas_object(source, index=False)
    reference_hashes = pd.util.hash_pandas_object(reference, index=False)
    reference_by_hash: dict[int, list[int]] = {}
    for index, row_hash in enumerate(reference_hashes.tolist()):
        reference_by_hash.setdefault(int(row_hash), []).append(index)

    source_values = source.to_numpy(dtype=object)
    reference_values = reference.to_numpy(dtype=object)
    mask = np.zeros(len(source), dtype=bool)
    for source_index, row_hash in enumerate(source_hashes.tolist()):
        candidates = reference_by_hash.get(int(row_hash), ())
        if not candidates:
            continue
        row = source_values[source_index]
        for reference_index in candidates:
            reference_row = reference_values[reference_index]
            equal = pd.isna(row) & pd.isna(reference_row)
            comparable = ~(pd.isna(row) | pd.isna(reference_row))
            if bool(np.all(equal | (comparable & (row == reference_row)))):
                mask[source_index] = True
                break
    return mask


def audit_train_test_overlap(
    train: pd.DataFrame, test: pd.DataFrame, label_column: str
) -> dict[str, Any]:
    """Audit exact full-record overlap and class counts without changing inputs."""
    if list(train.columns) != list(test.columns):
        raise ValueError("Train and test columns must match for an exact overlap audit.")
    test_overlap_mask = _exact_overlap_mask(test, train)
    train_overlap_mask = _exact_overlap_mask(train, test)
    overlap_classes = train.loc[train_overlap_mask, label_column].astype(str).value_counts()
    unique_overlapping_records = train.loc[train_overlap_mask].drop_duplicates().shape[0]
    return {
        "raw_train_rows": int(len(train)),
        "unique_train_rows": int(train.drop_duplicates().shape[0]),
        "training_duplicate_rows_beyond_unique": int(train.duplicated().sum()),
        "overlapping_train_rows": int(train_overlap_mask.sum()),
        "overlapping_test_rows": int(test_overlap_mask.sum()),
        "unique_overlapping_records": int(unique_overlapping_records),
        "overlap_by_attack_class": {
            str(label): int(count) for label, count in overlap_classes.items()
        },
        "test_rows_affected_percentage": float(100 * test_overlap_mask.mean()),
        "neither_train_rows": int((~train_overlap_mask).sum()),
        "expected_cleaned_training_rows": int(len(train) - train_overlap_mask.sum()),
        "test_overlap_mask": test_overlap_mask,
        "train_overlap_mask": train_overlap_mask,
    }


def _fit_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    numeric_columns = features.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_columns = [column for column in features.columns if column not in numeric_columns]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical_columns,
            )
        )
    return ColumnTransformer(transformers=transformers)


def preprocess_and_partition(
    config: DatasetConfig,
) -> dict[str, Any]:
    """Fit on train only, transform test, and save reproducible partitions."""
    config.validate()
    if config.train_dataset_path is None or config.test_dataset_path is None:
        raise ValueError("Separate train_dataset_path and test_dataset_path are required.")
    train = load_dataset(config.train_dataset_path)
    test = load_dataset(config.test_dataset_path)
    label_column = config.label_column
    if label_column is None or label_column not in train.columns:
        raise ValueError("A valid label_column is required.")
    if label_column not in test.columns:
        raise ValueError("The test dataset is missing the configured label column.")
    if set(test[label_column].dropna().astype(str)) - set(train[label_column].dropna().astype(str)):
        raise ValueError("The test dataset contains labels not observed in training.")

    overlap_audit = audit_train_test_overlap(train, test, label_column)
    overlap_mask = _exact_overlap_mask(train, test)
    cleaned_train = train.loc[~overlap_mask].copy()
    dropped = [column for column in config.dropped_features if column in train.columns]
    feature_columns = [
        column for column in train.columns if column != label_column and column not in dropped
    ]
    train_working = cleaned_train.dropna(subset=[label_column])
    test_working = test.dropna(subset=[label_column])
    preprocessor = _fit_preprocessor(train_working[feature_columns])
    x_train = np.asarray(
        preprocessor.fit_transform(train_working[feature_columns]), dtype=np.float32
    )
    x_test = np.asarray(
        preprocessor.transform(test_working[feature_columns]), dtype=np.float32
    )
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(train_working[label_column].astype(str))
    y_test = label_encoder.transform(test_working[label_column].astype(str))
    feature_names = [str(name) for name in preprocessor.get_feature_names_out()]

    config.output_dir.mkdir(parents=True, exist_ok=True)
    cleaned_train_path = config.output_dir / "train_data_leakage_free.csv"
    cleaned_train.to_csv(cleaned_train_path, index=False)
    artifacts_dir = config.output_dir / "artifacts"
    partitions_dir = config.output_dir / "operator_partitions"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    partitions_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "preprocessor": preprocessor,
            "label_encoder": label_encoder,
            "feature_columns": feature_columns,
            "dropped_features": dropped,
        },
        artifacts_dir / "preprocessing.joblib",
    )
    np.savez_compressed(config.output_dir / "test_preprocessed.npz", features=x_test, labels=y_test)

    def save_partitions(mode: str) -> dict[str, Any]:
        split = DatasetSplit(
            x_train=x_train,
            x_test=x_test,
            y_train=y_train,
            y_test=y_test,
            train_indices=np.arange(len(y_train)),
            test_indices=np.arange(len(y_test)),
        )
        partitions = partition_training_data(
            split, mode, config.random_seed, config.non_iid_concentration
        )
        report: dict[str, Any] = {}
        for name, partition in partitions.items():
            np.savez_compressed(
                partitions_dir / f"{mode}_{name}.npz",
                features=partition.x_train,
                labels=partition.y_train,
                source_indices=partition.source_indices,
            )
            labels, counts = np.unique(partition.y_train, return_counts=True)
            report[name] = {
                "rows": int(len(partition.y_train)),
                "class_distribution": {
                    str(label_encoder.classes_[int(label)]): int(count)
                    for label, count in zip(labels, counts)
                },
            }
        return report

    report = {
        "duplicate_overlap": {
            "raw_train_rows": overlap_audit["raw_train_rows"],
            "unique_train_rows": overlap_audit["unique_train_rows"],
            "training_duplicate_rows_beyond_unique": overlap_audit[
                "training_duplicate_rows_beyond_unique"
            ],
            "overlapping_train_rows": overlap_audit["overlapping_train_rows"],
            "overlapping_test_rows": overlap_audit["overlapping_test_rows"],
            "unique_overlapping_records": overlap_audit["unique_overlapping_records"],
            "overlap_by_attack_class": overlap_audit["overlap_by_attack_class"],
            "test_rows_affected_percentage": overlap_audit["test_rows_affected_percentage"],
            "neither_train_rows": overlap_audit["neither_train_rows"],
            "expected_cleaned_training_rows": overlap_audit[
                "expected_cleaned_training_rows"
            ],
            "training_duplicate_strategy": "retain_non_overlapping_training_duplicates",
            "training_duplicate_strategy_reason": (
                "All training row occurrences exactly matching a complete test record "
                "were removed. Duplicates occurring only within training were retained."
            ),
            "cleaned_training_rows": int(len(cleaned_train)),
            "remaining_exact_overlap": int(_exact_overlap_mask(test, cleaned_train).sum()),
        },
        "preprocessing": {
            "fit_on": str(cleaned_train_path),
            "source_train_dataset": str(config.train_dataset_path),
            "applied_to": [str(config.test_dataset_path), "operator training partitions"],
            "dropped_features": dropped,
            "feature_columns_before_encoding": feature_columns,
            "feature_count": len(feature_names),
            "feature_names": feature_names,
            "encoded_class_mapping": {
                str(label): int(index) for index, label in enumerate(label_encoder.classes_)
            },
        },
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
        "iid": save_partitions("iid"),
        "non_iid": save_partitions("non_iid"),
    }
    (config.output_dir / "preprocessing_partition_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def prepare_dataset(frame: pd.DataFrame, label_column: str) -> PreparedDataset:
    """Impute, encode, and scale observed feature columns; encode observed labels."""
    if label_column not in frame.columns:
        raise ValueError(f"Label column '{label_column}' was not found.")
    working = frame.dropna(subset=[label_column]).copy()
    features = working.drop(columns=[label_column])
    if features.shape[1] == 0:
        raise ValueError("The dataset must contain at least one feature column.")

    numeric_columns = features.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_columns = [column for column in features.columns if column not in numeric_columns]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical_columns,
            )
        )
    preprocessor = ColumnTransformer(transformers=transformers)
    encoded_features = preprocessor.fit_transform(features)
    encoder = LabelEncoder()
    encoded_labels = encoder.fit_transform(working[label_column].astype(str))
    feature_names = [str(name) for name in preprocessor.get_feature_names_out()]
    return PreparedDataset(
        features=np.asarray(encoded_features, dtype=np.float64),
        labels=encoded_labels,
        label_classes=[str(label) for label in encoder.classes_],
        feature_names=feature_names,
        label_encoder=encoder,
        preprocessor=preprocessor,
    )


def split_dataset(prepared: PreparedDataset, test_size: float, random_seed: int) -> DatasetSplit:
    """Create a reproducible, stratified split from prepared rows."""
    indices = np.arange(len(prepared.labels))
    train_indices, test_indices = train_test_split(
        indices,
        test_size=test_size,
        random_state=random_seed,
        stratify=prepared.labels,
    )
    return DatasetSplit(
        x_train=prepared.features[train_indices],
        x_test=prepared.features[test_indices],
        y_train=prepared.labels[train_indices],
        y_test=prepared.labels[test_indices],
        train_indices=train_indices,
        test_indices=test_indices,
    )


def _iid_indices(labels: np.ndarray, operator_count: int, random_seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(random_seed)
    buckets: list[list[int]] = [[] for _ in range(operator_count)]
    for label in np.unique(labels):
        label_indices = np.flatnonzero(labels == label)
        rng.shuffle(label_indices)
        for position, index in enumerate(label_indices):
            buckets[position % operator_count].append(int(index))
    return [np.asarray(sorted(bucket), dtype=int) for bucket in buckets]


def _non_iid_indices(
    labels: np.ndarray,
    operator_count: int,
    concentration: float,
    random_seed: int,
) -> list[np.ndarray]:
    rng = np.random.default_rng(random_seed)
    buckets: list[list[int]] = [[] for _ in range(operator_count)]
    for label in np.unique(labels):
        label_indices = np.flatnonzero(labels == label)
        rng.shuffle(label_indices)
        proportions = rng.dirichlet(np.full(operator_count, concentration))
        counts = rng.multinomial(len(label_indices), proportions)
        start = 0
        for operator_index, count in enumerate(counts):
            buckets[operator_index].extend(label_indices[start : start + count].tolist())
            start += count
    if any(not bucket for bucket in buckets):
        raise ValueError(
            "The configured non-IID partition produced an empty operator partition. "
            "Use more rows, increase concentration, or change the random seed."
        )
    return [np.asarray(sorted(bucket), dtype=int) for bucket in buckets]


def partition_training_data(
    split: DatasetSplit,
    mode: str,
    random_seed: int,
    concentration: float = 0.5,
) -> dict[str, OperatorPartition]:
    """Partition only training rows into four logically separate operator datasets."""
    if mode == "iid":
        partitions = _iid_indices(split.y_train, len(OPERATOR_NAMES), random_seed)
    elif mode == "non_iid":
        partitions = _non_iid_indices(
            split.y_train, len(OPERATOR_NAMES), concentration, random_seed
        )
    else:
        raise ValueError("mode must be either 'iid' or 'non_iid'.")
    return {
        name: OperatorPartition(
            name=name,
            x_train=split.x_train[indices],
            y_train=split.y_train[indices],
            source_indices=split.train_indices[indices],
        )
        for name, indices in zip(OPERATOR_NAMES, partitions)
    }


def build_report(config: DatasetConfig) -> dict[str, Any]:
    """Run inspection and preparation and return factual, serializable metadata."""
    config.validate()
    frame = load_dataset(config.dataset_path)
    inspection = inspect_dataset(frame, config.dataset_path, config.label_column)
    prepared = prepare_dataset(frame, inspection.label_column)
    split = split_dataset(prepared, config.test_size, config.random_seed)
    partitions = partition_training_data(
        split,
        config.partition_mode,
        config.random_seed,
        config.non_iid_concentration,
    )
    return {
        "inspection": inspection.to_dict(),
        "prepared": {
            "feature_count": len(prepared.feature_names),
            "feature_names": prepared.feature_names,
            "label_classes": prepared.label_classes,
        },
        "split": {"train_rows": len(split.y_train), "test_rows": len(split.y_test)},
        "operators": {
            name: {
                "train_rows": len(partition.y_train),
                "class_distribution": {
                prepared.label_classes[int(label)]: int(count)
                    for label, count in zip(*np.unique(partition.y_train, return_counts=True))
                },
            }
            for name, partition in partitions.items()
        },
    }


def run_from_config(config_path: Path) -> dict[str, Any]:
    config = DatasetConfig.from_json(config_path)
    report = build_report(config)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / "dataset_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def run_inspection_from_config(config_path: Path) -> dict[str, Any]:
    config = DatasetConfig.from_json(config_path)
    train_path = config.train_dataset_path or config.dataset_path / "train_data.csv"
    test_path = config.test_dataset_path or config.dataset_path / "test_data.csv"
    inspection = inspect_train_test(train_path, test_path, config.label_column)
    report = inspection.to_dict()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / "dataset_inspection_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
