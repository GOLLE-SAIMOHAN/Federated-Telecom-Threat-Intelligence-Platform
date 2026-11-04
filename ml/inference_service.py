"""Small authenticated HTTP wrapper for deploying inference as a Render service."""

import hmac
import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ml.inference import InferenceValidationError, initialize_inference, predict_csv

MAX_REQUEST_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000
LOGGER = logging.getLogger("inference_service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    force=True,
)


def _request_id(handler: BaseHTTPRequestHandler) -> str:
    value = handler.headers.get("X-Request-ID", "unknown")
    sanitized = "".join(character for character in value[:128] if character.isalnum() or character in "._:-")
    return sanitized or "unknown"

class InferenceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        trace_id = _request_id(self)
        started = time.monotonic()
        LOGGER.info("predict_received request_id=%s path=%s", trace_id, self.path)
        if self.path != "/predict":
            self._json_response(404, {"error": "Not found.", "code": "NOT_FOUND"})
            return
        expected_key = self.server.api_key
        provided_key = self.headers.get("X-Inference-API-Key", "")
        if not expected_key or not hmac.compare_digest(provided_key, expected_key):
            LOGGER.warning("predict_authentication_failed request_id=%s", trace_id)
            self._json_response(401, {"error": "Authentication required.", "code": "AUTHENTICATION_REQUIRED"})
            return
        if self.headers.get("content-type", "").split(";")[0].strip().lower() != "text/csv":
            self._json_response(415, {"error": "Content-Type must be text/csv.", "code": "CSV_CONTENT_TYPE_REQUIRED"})
            return
        raw_length = self.headers.get("content-length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 1:
            self._json_response(400, {"error": "A valid Content-Length is required.", "code": "INVALID_CONTENT_LENGTH"})
            return
        if length > MAX_REQUEST_BYTES:
            self._json_response(413, {"error": "The request exceeds the 5 MB limit.", "code": "CSV_SIZE_LIMIT"})
            return
        try:
            csv_text = self.rfile.read(length).decode("utf-8")
            LOGGER.info("csv_received request_id=%s bytes=%s", trace_id, length)
            result = predict_csv(csv_text)
            LOGGER.info(
                "csv_validation_succeeded request_id=%s records=%s",
                trace_id,
                result["processed_rows"],
            )
            LOGGER.info(
                "prediction_succeeded request_id=%s records_processed=%s elapsed_ms=%s",
                trace_id,
                result["processed_rows"],
                round((time.monotonic() - started) * 1000),
            )
            self._json_response(200, result)
        except (UnicodeDecodeError, InferenceValidationError) as error:
            LOGGER.warning("csv_validation_failed request_id=%s error=%s", trace_id, error)
            self._json_response(400, {"error": str(error), "code": "CSV_VALIDATION_ERROR"})
        except Exception:
            LOGGER.exception("prediction_failed request_id=%s", trace_id)
            self._json_response(500, {"error": "Inference processing failed.", "code": "INFERENCE_PROCESSING_ERROR"})

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
