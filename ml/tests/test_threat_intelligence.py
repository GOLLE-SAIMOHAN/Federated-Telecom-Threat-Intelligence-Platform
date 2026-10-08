from datetime import datetime, timezone

from ml.threat_intelligence import ThreatIntelligenceEngine


def test_threat_records_are_from_real_operator_predictions():
    engine = ThreatIntelligenceEngine(
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    records = engine.detect_operator("Operator A")

    assert records
    assert all(record.source_operator == "Operator A" for record in records)
    assert all(record.attack_type != "benign" for record in records)
    assert all(0.0 <= record.confidence <= 1.0 for record in records)
    assert all(record.model_version == "federated-iid-round-3" for record in records)


def test_propagation_contains_metadata_only_and_excludes_source():
    engine = ThreatIntelligenceEngine(
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    record = engine.detect_operator("Operator A")[0]
    propagated = engine.propagate([record])[0]

    assert propagated["recipient_operators"] == [
        "Operator B",
        "Operator C",
        "Operator D",
    ]
    assert propagated["event"]["threat_id"] == record.threat_id
    assert "features" not in propagated
    assert "labels" not in propagated
    assert "source_indices" not in propagated


def test_summary_groups_by_operator_attack_severity_and_status():
    engine = ThreatIntelligenceEngine(
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    records = engine.detect_operator("Operator A")[:2]
    summary = engine.aggregate(records)

    assert summary["artifact_type"] == "simulated_model_generated_detection_summary"
    assert summary["event_count"] == 2
    assert summary["grouped_by"] == [
        "operator",
        "attack_type",
        "severity",
        "status",
    ]
    assert sum(group["event_count"] for group in summary["groups"]) == 2
    assert all("average_confidence" in group for group in summary["groups"])
    assert all("features" not in group for group in summary["groups"])
