import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const maxOutputBytes = 16 * 1024 * 1024;

function log(level, event, details = {}) {
  console[level](JSON.stringify({ service: "backend", event, ...details }));
}

function errorDetails(error) {
  return {
    code: error?.code ?? "INFERENCE_ERROR",
    message: error instanceof Error ? error.message : String(error),
  };
}

function sanitizeResponsePreview(body, contentType) {
  if (contentType?.toLowerCase().includes("text/csv")) return "[redacted CSV response]";
  return body.slice(0, 200)
    .replace(/(?:api[-_ ]?key|authorization|token|secret)(\s*[:=]\s*)["']?[^"',\s]+["']?/gi, "$1[redacted]")
    .replace(/[\u0000-\u001f\u007f]/g, " ");
}

export function runInference(csv, requestId = "unknown") {
  if (process.env.INFERENCE_URL) {
    if (!process.env.INFERENCE_API_KEY) {
      const error = new Error("Inference service authentication is not configured.");
      error.statusCode = 503;
      error.code = "INFERENCE_AUTH_NOT_CONFIGURED";
      return Promise.reject(error);
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    const startedAt = performance.now();
    log("info", "inference_request_started", { request_id: requestId });
    return fetch(`${process.env.INFERENCE_URL.replace(/\/$/, "")}/predict`, {
      method: "POST",
      headers: {
        "content-type": "text/csv",
        "X-Inference-API-Key": process.env.INFERENCE_API_KEY,
        "X-Request-ID": requestId,
      },
      body: csv,
      signal: controller.signal,
    }).then(async (response) => {
      const elapsed_ms = Math.round(performance.now() - startedAt);
      let body;
      let responseText;
      try {
        responseText = await response.text();
        body = JSON.parse(responseText);
      } catch (error) {
        const contentType = response.headers.get("content-type") ?? "unknown";
        log("error", "inference_invalid_response", {
          request_id: requestId,
          status: response.status,
          status_text: response.statusText,
          content_type: contentType,
          response_body_length: responseText?.length ?? 0,
          response_body_preview: typeof responseText === "string"
            ? sanitizeResponsePreview(responseText, contentType)
            : "[unavailable]",
          elapsed_ms,
          error: errorDetails(error),
          stack: error instanceof Error ? error.stack : undefined,
        });
        const invalidResponse = new Error("Inference service returned an invalid response.");
        invalidResponse.statusCode = 503;
        invalidResponse.code = "INFERENCE_INVALID_RESPONSE";
        throw invalidResponse;
      }
      log(response.ok ? "info" : "error", "inference_response", {
        request_id: requestId,
        status: response.status,
        elapsed_ms,
        ...(response.ok ? {} : { upstream_error: body?.error, upstream_code: body?.code }),
      });
      if (!response.ok) {
        const error = new Error(body.error ?? "Inference service rejected the CSV.");
        error.statusCode = response.status >= 500 ? 503 : response.status;
        error.code = body.code ?? "INFERENCE_UPSTREAM_ERROR";
        throw error;
      }
      return body;
    }).catch((error) => {
      if (error.name === "AbortError") {
        log("error", "inference_timeout", {
          request_id: requestId,
          elapsed_ms: Math.round(performance.now() - startedAt),
          error: errorDetails(error),
          stack: error.stack,
        });
        const unavailable = new Error("Inference service is unavailable.");
        unavailable.statusCode = 503;
        unavailable.code = "INFERENCE_TIMEOUT";
        throw unavailable;
      }
      if (error.name === "TypeError") {
        log("error", "inference_network_error", {
          request_id: requestId,
          elapsed_ms: Math.round(performance.now() - startedAt),
          error: errorDetails(error),
          stack: error.stack,
        });
        const unavailable = new Error("Inference service is unavailable.");
        unavailable.statusCode = 503;
        unavailable.code = "INFERENCE_NETWORK_ERROR";
        throw unavailable;
      }
      if (!error.statusCode) {
        log("error", "inference_unexpected_error", {
          request_id: requestId,
          elapsed_ms: Math.round(performance.now() - startedAt),
          error: errorDetails(error),
          stack: error instanceof Error ? error.stack : undefined,
        });
      }
      throw error;
    }).finally(() => {
      clearTimeout(timeout);
    });
  }
  if (process.env.NODE_ENV === "production") {
    const error = new Error("Inference service URL is not configured.");
    error.statusCode = 503;
    error.code = "INFERENCE_URL_NOT_CONFIGURED";
    return Promise.reject(error);
  }
  const executable = process.env.PYTHON_EXECUTABLE ?? path.join(repositoryRoot, ".venv", "Scripts", "python.exe");
  const processedDir = process.env.PROCESSED_DATA_DIR ?? path.join(repositoryRoot, "data", "processed");
  return new Promise((resolve, reject) => {
  const child = spawn(executable, ["-m", "ml.inference", "--processed-dir", processedDir], {
      cwd: repositoryRoot,
      windowsHide: true,
    });
    let output = "";
    let errorOutput = "";
    child.stdout.on("data", (chunk) => {
      output += chunk;
      if (Buffer.byteLength(output) > maxOutputBytes) child.kill();
    });
    child.stderr.on("data", (chunk) => { errorOutput += chunk; });
    child.on("error", (error) => {
      log("error", "inference_process_error", {
        request_id: requestId,
        error: errorDetails(error),
        stack: error.stack,
      });
      const unavailable = new Error("Inference service is unavailable.");
      unavailable.code = "INFERENCE_PROCESS_ERROR";
      reject(unavailable);
    });
    child.on("close", (code) => {
      if (code !== 0) {
        let message = "Inference failed.";
        try { message = JSON.parse(errorOutput).error ?? message; } catch {}
        reject(new Error(message));
        return;
      }
      try { resolve(JSON.parse(output)); } catch { reject(new Error("Inference returned an invalid response.")); }
    });
    child.stdin.end(csv);
  });
}
