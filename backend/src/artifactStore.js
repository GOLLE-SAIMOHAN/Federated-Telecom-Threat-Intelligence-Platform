import fs from "node:fs/promises";
import path from "node:path";

const processedDirectory = path.resolve(
  process.env.PROCESSED_DATA_DIR ?? path.join("..", "data", "processed"),
);
const boundedThreatCount = 1000;

async function readJson(name) {
  const filePath = path.join(processedDirectory, name);
  const content = await fs.readFile(filePath, "utf8");
  return JSON.parse(content);
}

export async function loadArtifacts() {
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
