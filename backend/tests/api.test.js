import assert from "node:assert/strict";
import test from "node:test";
import { createApp } from "../src/app.js";

const artifacts = {
  centralized: { model: "RandomForestClassifier", metrics: { accuracy: 0.9 } },
  federated: {
    iid: { configuration: { clients: ["Operator A"], partition_mode: "iid", rounds: 5 } },
    non_iid: { configuration: { clients: ["Operator A"], partition_mode: "non_iid", rounds: 5 } },
  },
  summary: {
    artifact_type: "simulated_model_generated_detection_summary",
    event_count: 2,
    grouped_by: ["operator", "attack_type", "severity", "status"],
    groups: [
      {
        operator: "Operator A",
        attack_type: "DDoS",
        severity: "high",
        status: "new",
        event_count: 2,
      },
    ],
  },
  events: [
    {
      threat_id: "threat-1",
      attack_type: "DDoS",
      severity: "high",
      confidence: 0.9,
      source_operator: "Operator A",
      status: "new",
    },
    {
      threat_id: "threat-2",
      attack_type: "DDoS",
      severity: "high",
      confidence: 0.8,
      source_operator: "Operator A",
      status: "new",
    },
  ],
  boundedEvents: [
    {
      threat_id: "threat-1",
      attack_type: "DDoS",
      severity: "high",
      confidence: 0.9,
      source_operator: "Operator A",
      status: "new",
    },
    {
      threat_id: "threat-2",
      attack_type: "DDoS",
      severity: "high",
      confidence: 0.8,
      source_operator: "Operator A",
      status: "new",
    },
  ],
};

const app = createApp({
  artifacts,
  mongoStore: { status: () => ({ configured: false, connected: false, error: null }) },
});

async function get(path) {
  const server = app.listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}${path}`);
  const body = await response.json();
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  return { response, body };
}

test("serves health and actual federated data", async () => {
  const health = await get("/api/health");
  assert.equal(health.response.status, 200);
  assert.equal(health.body.status, "ok");

  const federated = await get("/api/federated");
  assert.equal(federated.body.iid.configuration.rounds, 5);
});

test("validates bounded threat limit and supports lookup", async () => {
  const threats = await get("/api/threats?limit=1");
  assert.equal(threats.body.threats.length, 1);

  const invalid = await get("/api/threats?limit=0");
  assert.equal(invalid.response.status, 400);

  const detail = await get("/api/threats/threat-1");
  assert.equal(detail.body.threat_id, "threat-1");
});

test("returns an honest empty threat list when no events are available", async () => {
  const emptyApp = createApp({
    artifacts: { ...artifacts, events: [], boundedEvents: [], summary: { ...artifacts.summary, event_count: 0 } },
    mongoStore: { status: () => ({ configured: false, connected: false, error: null }) },
  });

  test("accepts a validated CSV detection request", async () => {
    const detectionApp = createApp({
      artifacts,
      mongoStore: { status: () => ({ configured: false, connected: false, error: null }) },
      inference: async () => ({
        model_version: "federated_iid_rounds_5",
        processed_rows: 1,
        benign_count: 1,
        attack_count: 0,
        predictions: [{ row_number: 2, predicted_class: "benign", model_score: 0.99 }],
        summary: [{ predicted_class: "benign", count: 1 }],
        attack_events: [],
      }),
    });
    const server = detectionApp.listen(0);
    await new Promise((resolve) => server.once("listening", resolve));
    const address = server.address();
    const response = await fetch(`http://127.0.0.1:${address.port}/api/detection`, {
      method: "POST",
      headers: { "content-type": "text/csv" },
      body: "ip.len,tcp.port\n1,2\n",
    });
    const body = await response.json();
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
    assert.equal(response.status, 200);
    assert.equal(body.processed_rows, 1);
  });
  const server = emptyApp.listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}/api/threats`);
  const body = await response.json();
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  assert.equal(response.status, 200);
  assert.deepEqual(body.threats, []);
});
