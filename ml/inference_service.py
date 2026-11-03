"""Small authenticated HTTP wrapper for deploying inference as a Render service."""

import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ml.inference import InferenceValidationError, initialize_inference, predict_csv

MAX_REQUEST_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000

class InferenceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/predict":
            self._json_response(404, {"error": "Not found."})
            return
        expected_key = self.server.api_key
        provided_key = self.headers.get("X-Inference-API-Key", "")
        if not expected_key or not hmac.compare_digest(provided_key, expected_key):
            self._json_response(401, {"error": "Authentication required."})
            return
        if self.headers.get("content-type", "").split(";")[0].strip().lower() != "text/csv":
            self._json_response(415, {"error": "Content-Type must be text/csv."})
            return
        raw_length = self.headers.get("content-length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 1:
            self._json_response(400, {"error": "A valid Content-Length is required."})
            return
        if length > MAX_REQUEST_BYTES:
            self._json_response(413, {"error": "The request exceeds the 5 MB limit."})
            return
        try:
            csv_text = self.rfile.read(length).decode("utf-8")
            result = predict_csv(csv_text)
            self._json_response(200, result)
        except (UnicodeDecodeError, InferenceValidationError) as error:
            self._json_response(400, {"error": str(error)})
        except Exception:
            self._json_response(500, {"error": "Inference processing failed."})

    def do_GET(self) -> None:
        if self.path != "/health":
            self._json_response(404, {"error": "Not found."})
            return
        if self.server.runtime_loaded:
            self._json_response(200, {"status": "ok", "service": "federated-telecom-inference"})
        else:
            self._json_response(503, {"status": "unavailable", "service": "federated-telecom-inference"})

    def _json_response(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


if __name__ == "__main__":
    api_key = os.environ.get("INFERENCE_API_KEY")
    if not api_key:
        print("INFERENCE_API_KEY is required.", file=sys.stderr)
        raise SystemExit(1)
    try:
        initialize_inference()
    except Exception as error:
        print(f"Inference artifacts could not be loaded: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), InferenceHandler)
    server.api_key = api_key
    server.runtime_loaded = True
    server.serve_forever()
