"""Small HTTP wrapper for deploying inference as a separate Render service."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os

from ml.inference import predict_csv


class InferenceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/predict" or self.headers.get("content-type", "").split(";")[0] != "text/csv":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        csv_text = self.rfile.read(length).decode("utf-8")
        try:
            import json
            body = json.dumps(predict_csv(csv_text)).encode("utf-8")
            self.send_response(200)
        except Exception as error:
            import json
            body = json.dumps({"error": str(error)}).encode("utf-8")
            self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), InferenceHandler).serve_forever()
