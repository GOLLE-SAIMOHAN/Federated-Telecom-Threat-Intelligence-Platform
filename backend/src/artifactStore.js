import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendDirectory = path.dirname(fileURLToPath(import.meta.url));
const defaultBackendDataDirectory = path.resolve(backendDirectory, "..", "data");
const processedDirectory = path.resolve(
  process.env.PROCESSED_DATA_DIR ??
    path.resolve(backendDirectory, "..", "..", "data", "processed"),
);
const boundedThreatCount = 1000;

async function readJson(name) {
  const filePath = path.join(processedDirectory, name);
  const content = await fs.readFile(filePath, "utf8");
  return JSON.parse(content);
}

export async function loadArtifacts() {
  const snapshotPath =
    process.env.DEMO_ARTIFACTS_PATH ??
    path.join(defaultBackendDataDirectory, "demo-artifacts.json");
  const snapshot = snapshotPath
    ? JSON.parse(await fs.readFile(path.resolve(snapshotPath), "utf8"))
    : null;
  if (snapshot) {
    return {
      ...snapshot,
      boundedEvents: snapshot.events.slice(0, boundedThreatCount),
      processedDirectory,
    };
  }
  const [federated, summary, events, propagation] = await Promise.all([
    readJson("federated_iid_report.json"),
    readJson("threat_summary.json"),
    readJson("threat_events.json"),
    readJson("threat_propagation.json"),
  ]);

  return {
    federated,
    summary,
    events,
    propagation,
    boundedEvents: events.slice(0, boundedThreatCount),
    processedDirectory,
  };
}

export { boundedThreatCount };
