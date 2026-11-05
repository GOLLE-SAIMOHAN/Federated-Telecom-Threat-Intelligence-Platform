import cors from "cors";
import { randomUUID } from "node:crypto";
import express from "express";
import { runInference } from "./inferenceRunner.js";

function publicDetectionError(error) {
  const message = error instanceof Error ? error.message : "";
  if (/^(CSV|Missing required|Column '.*' contains|The CSV)/.test(message)) return message;
  return "Detection service could not process the uploaded CSV.";
}

function requestId(request) {
  const supplied = request.get("X-Request-ID")?.trim();
  return supplied && /^[A-Za-z0-9._:-]{1,128}$/.test(supplied) ? supplied : randomUUID();
}

function logDetection(level, event, details = {}) {
  console[level](JSON.stringify({ service: "backend", event, ...details }));
}

function queryStringValue(value) {
  return typeof value === "string" ? value : null;
}

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

export function createApp({ artifacts, mongoStore, inference = runInference }) {
  const app = express();
  app.disable("x-powered-by");
  const configuredOrigins = process.env.CORS_ORIGIN
    ?.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  app.use(cors({
    origin: configuredOrigins?.length ? configuredOrigins : true,
  }));
  app.use(express.json({ limit: "64kb" }));
  const uploadLimit = process.env.DETECTION_MAX_BYTES ?? "5mb";
  app.use("/api/detection", express.raw({
    type: ["text/csv", "application/csv", "application/octet-stream"],
    limit: uploadLimit,
  }));

  app.get("/api/health", (_request, response) => {
    response.json({ status: "ok", service: "federated-telecom-backend" });
  });

  app.get("/api/system/status", (_request, response) => {
    response.json({
      status: "ok",
      data_source: "local_processed_artifacts",
      simulated_detection_events: true,
      federated: {
        experiments: ["iid", "non_iid"],
        rounds: artifacts.federated.iid.configuration.rounds,
        clients: artifacts.federated.iid.configuration.clients,
      },
      threat_event_count: artifacts.summary.event_count,
      bounded_threat_records: artifacts.boundedEvents.length,
      mongodb: mongoStore.status(),
    });
  });

  app.get("/api/operators", (_request, response) => {
    response.json({ operators: artifacts.operators ?? createOperators(artifacts.summary) });
  });

  app.get("/api/federated", (_request, response) => {
    response.json({
      iid: artifacts.federated.iid,
      non_iid: artifacts.federated.non_iid,
    });
  });

  app.get("/api/centralized", (_request, response) => {
    response.json(artifacts.centralized);
  });

  app.get("/api/experiments", (_request, response) => {
    response.json({
      centralized: artifacts.centralized,
      federated: {
        iid: artifacts.federated.iid,
        non_iid: artifacts.federated.non_iid,
      },
    });
  });

  app.get("/api/threats/summary", (_request, response) => {
    response.json(artifacts.summary);
  });

  app.get("/api/threats", async (request, response) => {
    const rawLimit = request.query.limit ?? "50";
    const limit = Number(rawLimit);
    if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
      response.status(400).json({
        error: "limit must be an integer between 1 and 50",
      });
      return;
    }
    if (!mongoStore.listCtiEvents) {
      response.json({
        simulated_detection_events: true,
        limit,
        total_available_in_local_artifact: artifacts.events.length,
        threats: artifacts.boundedEvents.slice(0, limit),
      });
      return;
    }
    try {
      const result = await mongoStore.listCtiEvents(limit);
      response.json({
        simulated_detection_events: false,
        limit,
        total: result.total,
        threats: result.events,
      });
    } catch (error) {
      logDetection("error", "cti_event_list_failed", {
        error: error instanceof Error ? error.message : String(error),
      });
      response.status(503).json({ error: "Threat intelligence records are temporarily unavailable." });
    }
  });

  app.get("/api/threats/:id", async (request, response) => {
    if (!mongoStore.getCtiEvent) {
      const threat = artifacts.boundedEvents.find(
        (event) => event.threat_id === request.params.id,
      );
      if (!threat) {
        response.status(404).json({ error: "Threat record not found in bounded API view" });
        return;
      }
      response.json(threat);
      return;
    }
    try {
      const event = await mongoStore.getCtiEvent(request.params.id);
      if (!event) {
        response.status(404).json({ error: "Threat intelligence event not found" });
        return;
      }
      response.json(event);
    } catch (error) {
      logDetection("error", "cti_event_retrieval_failed", {
        error: error instanceof Error ? error.message : String(error),
      });
      response.status(503).json({ error: "Threat intelligence record is temporarily unavailable." });
    }
  });

  app.get("/api/detections", async (request, response) => {
    const rawPage = queryStringValue(request.query.page) ?? "1";
    const rawLimit = queryStringValue(request.query.limit) ?? "10";
    const page = Number(rawPage);
    const limit = Number(rawLimit);
    const search = queryStringValue(request.query.search)?.trim() || null;
    const attackType = queryStringValue(request.query.attack_type)?.trim() || null;
    if (!Number.isInteger(page) || page < 1) {
      response.status(400).json({ error: "page must be a positive integer" });
      return;
    }
    if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
      response.status(400).json({ error: "limit must be an integer between 1 and 50" });
      return;
    }
    if (request.query.search !== undefined && search === null) {
      response.status(400).json({ error: "search must be a string" });
      return;
    }
    if (request.query.attack_type !== undefined && attackType === null) {
      response.status(400).json({ error: "attack_type must be a string" });
      return;
    }
    try {
      const result = await mongoStore.listDetections({
        page,
        limit,
        search,
        attackType,
      });
      response.json({
        detections: result.detections,
        total: result.total,
        pagination: {
          page,
          limit,
          total_pages: Math.ceil(result.total / limit),
        },
      });
    } catch (error) {
      logDetection("error", "detection_list_failed", {
        error: error instanceof Error ? error.message : String(error),
      });
      response.status(503).json({ error: "Detection records are temporarily unavailable." });
    }
  });

  app.get("/api/detections/:id", async (request, response) => {
    try {
      const detection = await mongoStore.getDetection(request.params.id);
      if (!detection) {
        response.status(404).json({ error: "Detection record not found" });
        return;
      }
      response.json(detection);
    } catch (error) {
      logDetection("error", "detection_retrieval_failed", {
        error: error instanceof Error ? error.message : String(error),
      });
      response.status(503).json({ error: "Detection record is temporarily unavailable." });
    }
  });

  app.post("/api/detection", async (request, response) => {
    const traceId = requestId(request);
    const startedAt = performance.now();
    response.setHeader("X-Request-ID", traceId);
    logDetection("info", "detection_request_started", { request_id: traceId });
    if (!Buffer.isBuffer(request.body) || request.body.length === 0) {
      logDetection("error", "detection_request_rejected", {
        request_id: traceId,
        code: "EMPTY_CSV",
      });
      response.status(400).json({ error: "Send a non-empty CSV file with Content-Type text/csv." });
      return;
    }
    try {
      logDetection("info", "inference_call_started", { request_id: traceId });
      const result = await inference(request.body.toString("utf8"), traceId);
      let persistence = { configured: mongoStore.status().configured, persisted: false, status: "not_saved" };
      try {
        if (result.attack_events?.length && mongoStore.persistDetectionEvents) {
          await mongoStore.persistDetectionEvents(result.attack_events);
        }
      } catch (error) {
        logDetection("error", "detection_persistence_failed", {
          request_id: traceId,
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        });
      }
      try {
        if (mongoStore.persistDetection) {
          const saved = await mongoStore.persistDetection({
            detection_id: traceId,
            created_at: new Date(),
            filename: request.get("X-Filename")?.trim() || "uploaded.csv",
            processed_rows: result.processed_rows,
            benign_count: result.benign_count,
            attack_count: result.attack_count,
            summary: result.summary,
            predictions: result.predictions,
            model_version: result.model_version,
            request_id: traceId,
          });
          persistence = { ...persistence, persisted: saved, status: saved ? "saved" : "not_saved" };
          if (saved && mongoStore.persistCtiEvents) {
            try {
              await mongoStore.persistCtiEvents({
                detectionId: traceId,
                predictions: result.predictions,
                modelVersion: result.model_version,
                createdAt: new Date(),
              });
            } catch (error) {
              logDetection("error", "cti_persistence_failed", {
                request_id: traceId,
                error: error instanceof Error ? error.message : String(error),
                stack: error instanceof Error ? error.stack : undefined,
              });
            }
          }
        }
      } catch (error) {
        logDetection("error", "detection_persistence_failed", {
          request_id: traceId,
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        });
      }
      logDetection("info", "detection_request_succeeded", {
        request_id: traceId,
        elapsed_ms: Math.round(performance.now() - startedAt),
        processed_rows: result.processed_rows,
      });
      response.json({ ...result, persistence });
    } catch (error) {
      const message = publicDetectionError(error);
      logDetection("error", "detection_request_failed", {
        request_id: traceId,
        elapsed_ms: Math.round(performance.now() - startedAt),
        code: error?.code ?? "DETECTION_FAILED",
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      response.status(error?.statusCode ?? (message.includes("limit") ? 413 : 400)).json({
        error: message,
        code: error?.code ?? "DETECTION_FAILED",
        request_id: traceId,
      });
    }
  });

  app.use((error, _request, response, _next) => {
    if (error?.type === "entity.too.large") {
      response.status(413).json({ error: "The uploaded CSV exceeds the configured size limit." });
      return;
    }
    response.status(400).json({ error: "The request could not be processed." });
  });

  app.use((_request, response) => {
    response.status(404).json({ error: "Not found" });
  });

  return app;
}
