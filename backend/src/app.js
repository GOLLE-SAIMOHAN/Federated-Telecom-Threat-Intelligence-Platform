import cors from "cors";
import express from "express";

function createOperators(summary) {
  const operators = new Map();
  for (const group of summary.groups) {
    const current = operators.get(group.operator) ?? {
      operator: group.operator,
      event_count: 0,
      attack_types: new Set(),
    };
    current.event_count += group.event_count;
    current.attack_types.add(group.attack_type);
    operators.set(group.operator, current);
  }
  return [...operators.values()].map((operator) => ({
    ...operator,
    attack_types: [...operator.attack_types].sort(),
  }));
}

export function createApp({ artifacts, mongoStore }) {
  const app = express();
  app.disable("x-powered-by");
  app.use(cors());
  app.use(express.json({ limit: "64kb" }));

  app.get("/api/health", (_request, response) => {
    response.json({ status: "ok", service: "federated-telecom-backend" });
  });

  app.get("/api/system/status", (_request, response) => {
    response.json({
      status: "ok",
      data_source: "local_processed_artifacts",
      simulated_detection_events: true,
      federated: {
        partition_mode: artifacts.federated.configuration.partition_mode,
        rounds: artifacts.federated.configuration.rounds,
        clients: artifacts.federated.configuration.clients,
      },
      threat_event_count: artifacts.summary.event_count,
      bounded_threat_records: artifacts.boundedEvents.length,
      mongodb: mongoStore.status(),
    });
  });

  app.get("/api/operators", (_request, response) => {
    response.json({ operators: createOperators(artifacts.summary) });
  });

  app.get("/api/federated", (_request, response) => {
    response.json(artifacts.federated);
  });

  app.get("/api/threats/summary", (_request, response) => {
    response.json(artifacts.summary);
  });

  app.get("/api/threats", (request, response) => {
    const rawLimit = request.query.limit ?? "50";
    const limit = Number(rawLimit);
    if (!Number.isInteger(limit) || limit < 1 || limit > artifacts.boundedEvents.length) {
      response.status(400).json({
        error: `limit must be an integer between 1 and ${artifacts.boundedEvents.length}`,
      });
      return;
    }
    response.json({
      simulated_detection_events: true,
      limit,
      total_available_in_local_artifact: artifacts.events.length,
      threats: artifacts.boundedEvents.slice(0, limit),
    });
  });

  app.get("/api/threats/:id", (request, response) => {
    const threat = artifacts.boundedEvents.find(
      (event) => event.threat_id === request.params.id,
    );
    if (!threat) {
      response.status(404).json({ error: "Threat record not found in bounded API view" });
      return;
    }
    response.json(threat);
  });

  app.use((_request, response) => {
    response.status(404).json({ error: "Not found" });
  });

  return app;
}
