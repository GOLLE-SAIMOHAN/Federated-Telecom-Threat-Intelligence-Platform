import pandas as pd
import pytest

from ml.inference import InferenceValidationError, predict_csv, predict_frame


FEATURES = [
    "ip.len", "ip.flags.df", "ip.flags.mf", "tcp.port", "tcp.ack_raw",
    "ip.ttl", "ip.proto", "tcp.window_size.1", "tcp.ack", "tcp.seq",
    "tcp.len", "tcp.stream", "tcp.urgent_pointer", "tcp.flags",
    "tcp.analysis.ack_rtt", "http.request", "frame.time_relative",
    "frame.time_delta", "tcp.time_relative", "tcp.time_delta", "tcp.srcport",
    "tcp.dstport", "http.request.uri",
]


def sample_frame() -> pd.DataFrame:
    row = {feature: 0 for feature in FEATURES}
    row["tcp.flags"] = "0x0010"
    row["http.request.uri"] = "/"
    row["attack"] = "should be ignored"
    return pd.DataFrame([row, row])


def test_reconstructs_model_and_excludes_target():
    result = predict_frame(sample_frame())
    assert result["processed_rows"] == 2
    assert len(result["predictions"]) == 2
    assert result["predictions"][0]["predicted_class"] in {"benign", "DDoS", "Brute Force", "Device Spoofing", "DoS_MQTT", "Eavesdropping", "MITM", "SQL Injection", "Unauthorized Data Access"}
    assert sum(item["count"] for item in result["summary"]) == 2


def test_missing_feature_is_rejected():
    frame = sample_frame().drop(columns=["tcp.port"])
    with pytest.raises(InferenceValidationError, match="tcp.port"):
        predict_frame(frame)


def test_invalid_numeric_feature_is_rejected():
    frame = sample_frame()
    frame.loc[0, "ip.len"] = "not-a-number"
    with pytest.raises(InferenceValidationError, match="ip.len"):
        predict_frame(frame)


def test_empty_csv_is_rejected():
    with pytest.raises(InferenceValidationError):
        predict_csv("")
