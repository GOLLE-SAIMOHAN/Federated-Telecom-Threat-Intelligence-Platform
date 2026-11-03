import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const maxOutputBytes = 16 * 1024 * 1024;

export function runInference(csv) {
  if (process.env.INFERENCE_URL) {
    return fetch(`${process.env.INFERENCE_URL.replace(/\/$/, "")}/predict`, {
      method: "POST",
      headers: { "content-type": "text/csv" },
      body: csv,
    }).then(async (response) => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.error ?? "Inference service rejected the CSV.");
      return body;
    });
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
    child.on("error", () => reject(new Error("Inference service is unavailable.")));
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
