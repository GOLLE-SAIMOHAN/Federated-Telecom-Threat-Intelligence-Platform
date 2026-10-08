"""Threat intelligence derived from actual federated model predictions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
from sklearn.linear_model import SGDClassifier

from ml.federated.simulation import CLIENT_NAMES


@dataclass(frozen=True)
class ThreatRecord:
    threat_id: str
    attack_type: str
    severity: str
    confidence: float
    timestamp: str
    source_operator: str
    model_version: str
    status: str
    event_type: str = "simulated_model_generated_detection"


def _severity(confidence: float) -> str:
    if confidence >= 0.90:
        return "critical"
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


def _utc_timestamp(value: datetime | None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ThreatIntelligenceEngine:
    """Create and propagate CTI without exposing local feature or label arrays."""

    def __init__(
        self,
        processed_dir: Path = Path("data/processed"),
        partition_mode: str = "iid",
        model_version: str | None = None,
        event_time: datetime | None = None,
    ) -> None:
        if partition_mode not in {"iid", "non_iid"}:
            raise ValueError("partition_mode must be 'iid' or 'non_iid'.")
        self.processed_dir = processed_dir
        self.partition_mode = partition_mode
        self.model_path = processed_dir / f"federated_{partition_mode}_model.joblib"
        self.report_path = processed_dir / f"federated_{partition_mode}_report.json"
        self.artifacts = joblib.load(
            processed_dir / "artifacts" / "preprocessing.joblib"
        )
        self.model_data = joblib.load(self.model_path)
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        rounds = report["configuration"]["rounds"]
        self.model_version = model_version or f"federated-{partition_mode}-round-{rounds}"
        self.timestamp = _utc_timestamp(event_time)
        self.class_names = self.artifacts["label_encoder"].classes_.tolist()

    def _model(self) -> SGDClassifier:
        parameters = self.model_data["parameters"]
        model = SGDClassifier(loss="log_loss", class_weight="balanced", random_state=42)
        model.classes_ = np.arange(len(self.class_names))
        model.coef_ = np.asarray(parameters[0], dtype=np.float64)
        model.intercept_ = np.asarray(parameters[1], dtype=np.float64)
        model.n_features_in_ = model.coef_.shape[1]
        return model

    def detect_operator(self, operator: str) -> list[ThreatRecord]:
        if operator not in CLIENT_NAMES:
            raise ValueError(f"Unknown operator: {operator}.")
        index = CLIENT_NAMES.index(operator)
        partition_file = (
            self.processed_dir
            / "operator_partitions"
            / f"{self.partition_mode}_operator_{chr(ord('a') + index)}.npz"
        )
        partition = np.load(partition_file)
        model = self._model()
        predictions = model.predict(partition["features"])
        probabilities = model.predict_proba(partition["features"])
        records: list[ThreatRecord] = []
        for row_index, (encoded, probability_row) in enumerate(
            zip(predictions, probabilities)
        ):
            attack_type = self.class_names[int(encoded)]
            if attack_type == "benign":
                continue
            confidence = float(np.max(probability_row))
            digest = hashlib.sha256(
                f"{operator}|{row_index}|{attack_type}|{self.model_version}".encode(
                    "utf-8"
                )
            ).hexdigest()[:20]
            records.append(
                ThreatRecord(
                    threat_id=f"threat-{digest}",
                    attack_type=attack_type,
                    severity=_severity(confidence),
                    confidence=confidence,
                    timestamp=self.timestamp,
                    source_operator=operator,
                    model_version=self.model_version,
                    status="new",
                )
            )
        return records

    def detect_all(self) -> list[ThreatRecord]:
        records: list[ThreatRecord] = []
        for operator in CLIENT_NAMES:
            records.extend(self.detect_operator(operator))
        return records

    @staticmethod
    def propagate(
        records: Iterable[ThreatRecord],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for record in records:
            payload = asdict(record)
            recipients = [
                operator for operator in CLIENT_NAMES if operator != record.source_operator
            ]
            events.append(
                {
                    "threat_id": record.threat_id,
                    "source_operator": record.source_operator,
                    "recipient_operators": recipients,
                    "event": payload,
                }
            )
        return events

    @staticmethod
    def aggregate(records: Iterable[ThreatRecord]) -> dict[str, Any]:
        groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        total = 0
        for record in records:
            total += 1
            key = (
                record.source_operator,
                record.attack_type,
                record.severity,
                record.status,
            )
            group = groups.setdefault(
                key,
                {
                    "operator": record.source_operator,
                    "attack_type": record.attack_type,
                    "severity": record.severity,
                    "status": record.status,
                    "event_count": 0,
                    "confidence_sum": 0.0,
                },
            )
            group["event_count"] += 1
            group["confidence_sum"] += record.confidence

        summaries = []
        for group in sorted(groups.values(), key=lambda item: (
            item["operator"],
            item["attack_type"],
            item["severity"],
            item["status"],
        )):
            count = group.pop("event_count")
            confidence_sum = group.pop("confidence_sum")
            summaries.append(
                {
                    **group,
                    "event_count": count,
                    "average_confidence": confidence_sum / count,
                }
            )
        return {
            "artifact_type": "simulated_model_generated_detection_summary",
            "event_count": total,
            "grouped_by": ["operator", "attack_type", "severity", "status"],
            "groups": summaries,
        }

    def save(self, records: list[ThreatRecord]) -> tuple[Path, Path, Path]:
        threat_path = self.processed_dir / "threat_events.json"
        propagation_path = self.processed_dir / "threat_propagation.json"
        summary_path = self.processed_dir / "threat_summary.json"
        threat_path.write_text(
            json.dumps([asdict(record) for record in records], indent=2),
            encoding="utf-8",
        )
        propagation_path.write_text(
            json.dumps(self.propagate(records), indent=2),
            encoding="utf-8",
        )
        summary_path.write_text(
            json.dumps(self.aggregate(records), indent=2),
            encoding="utf-8",
        )
        return threat_path, propagation_path, summary_path


if __name__ == "__main__":
    engine = ThreatIntelligenceEngine()
    events = engine.detect_all()
    paths = engine.save(events)
    print(
        json.dumps(
            {
                "event_count": len(events),
                "artifact_type": "simulated_model_generated_detection",
                "files": [str(path) for path in paths],
            }
        )
    )
