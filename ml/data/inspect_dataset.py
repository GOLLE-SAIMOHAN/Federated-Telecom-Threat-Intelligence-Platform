"""Command-line entry point for inspecting the real train/test dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.data.pipeline import preprocess_and_partition, run_inspection_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/dataset.json"),
        help="Path to the JSON dataset configuration.",
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Fit preprocessing on train data and create operator partitions.",
    )
    args = parser.parse_args()
    if args.preprocess:
        from ml.data.pipeline import DatasetConfig

        report = preprocess_and_partition(DatasetConfig.from_json(args.config))
    else:
        report = run_inspection_from_config(args.config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
