import http.client
import json
import socket
import threading
from pathlib import Path

import joblib

from ml.inference import initialize_inference
from ml.inference_service import InferenceHandler, MAX_REQUEST_BYTES
from http.server import ThreadingHTTPServer


def _server():
    initialize_inference(Path("data/processed"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), InferenceHandler)
    server.api_key = "test-key"
    server.runtime_loaded = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server, method, path, body=None, key=None, content_type="text/csv"):
    connection = http.client.HTTPConnection(*server.server_address)
    headers = {"Content-Type": content_type}
    if key is not None:
        headers["X-Inference-API-Key"] = key
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, json.loads(payload)


def _valid_csv():
    artifacts = joblib.load(Path("data/processed/artifacts/preprocessing.joblib"))
    row = {column: 0 for column in artifacts["feature_columns"]}
    row["tcp.flags"] = "0x0010"
    row["http.request.uri"] = "/"
    columns = artifacts["feature_columns"]
    return ",".join(columns) + "\n" + ",".join(str(row[column]) for column in columns) + "\n"


def test_health_authentication_validation_and_prediction():
    server, thread = _server()
    try:
        assert _request(server, "GET", "/health")[0] == 200
        assert _request(server, "POST", "/predict", _valid_csv())[0] == 401
        assert _request(server, "POST", "/predict", "not,a,valid,schema\n1,2,3,4\n", "test-key")[0] == 400
        status, result = _request(server, "POST", "/predict", _valid_csv(), "test-key")
        assert status == 200
        assert result["processed_rows"] == 1
    finally:
        server.shutdown()
        thread.join()


def test_oversized_request_is_rejected():
    server, thread = _server()
    try:
        connection = socket.create_connection(server.server_address)
        request = (
            f"POST /predict HTTP/1.1\r\nHost: localhost\r\n"
            f"Content-Type: text/csv\r\nX-Inference-API-Key: test-key\r\n"
            f"Content-Length: {MAX_REQUEST_BYTES + 1}\r\n\r\n"
        ).encode()
        connection.sendall(request)
        response = connection.recv(1024).decode()
        connection.close()
        assert "413" in response
    finally:
        server.shutdown()
        thread.join()
