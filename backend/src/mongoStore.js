import { MongoClient } from "mongodb";
import { isIP } from "node:net";

const IOC_FIELDS = new Map([
  ["ip.src", "ip"],
  ["ip.dst", "ip"],
  ["src_ip", "ip"],
  ["dst_ip", "ip"],
  ["source_ip", "ip"],
  ["destination_ip", "ip"],
  ["ipv4.src", "ip"],
  ["ipv4.dst", "ip"],
  ["domain", "domain"],
  ["hostname", "domain"],
  ["http.host", "domain"],
  ["dns.qry.name", "domain"],
  ["dns.resp.name", "domain"],
  ["url", "url"],
  ["full_url", "url"],
  ["http.request.full_uri", "url"],
  ["md5", "md5"],
  ["sha1", "sha1"],
  ["sha256", "sha256"],
  ["file_md5", "md5"],
  ["file_sha1", "sha1"],
  ["file_sha256", "sha256"],
  ["file_hash_md5", "md5"],
  ["file_hash_sha1", "sha1"],
  ["file_hash_sha256", "sha256"],
  ["file.md5", "md5"],
  ["file.sha1", "sha1"],
  ["file.sha256", "sha256"],
  ["file.hash.md5", "md5"],
  ["file.hash.sha1", "sha1"],
  ["file.hash.sha256", "sha256"],
]);

function validIoc(type, rawValue) {
  if (typeof rawValue !== "string" && typeof rawValue !== "number") return null;
  const value = String(rawValue).trim();
  if (!value) return null;
  if (type === "ip") return isIP(value) ? { value, normalizedValue: value } : null;
  if (type === "url") {
    try {
      const parsed = new URL(value);
      if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) return null;
      return { value, normalizedValue: parsed.href };
    } catch {
      return null;
    }
  }
  if (type === "domain") {
    if (value.length > 253 || !/^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}\.?$/.test(value)) return null;
    return { value, normalizedValue: value.toLowerCase().replace(/\.$/, "") };
  }
  const lengths = { md5: 32, sha1: 40, sha256: 64 };
  return new RegExp(`^[a-fA-F0-9]{${lengths[type]}}$`).test(value)
    ? { value, normalizedValue: value.toLowerCase() }
    : null;
}

function extractIocs(predictions, detectionId, modelVersion, createdAt) {
  const records = [];
  const visit = (value, path, prediction, rowNumber) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return;
    for (const [field, fieldValue] of Object.entries(value)) {
      const fieldPath = path ? `${path}.${field}` : field;
      const type = IOC_FIELDS.get(fieldPath) ?? IOC_FIELDS.get(field);
      if (type) {
        const valid = validIoc(type, fieldValue);
        if (valid) {
          records.push({
            ioc_id: `${detectionId}:${rowNumber}:${type}:${valid.normalizedValue}:${fieldPath}`,
            ioc_type: type,
            value: valid.value,
            normalized_value: valid.normalizedValue,
            source_field: fieldPath,
            detection_id: detectionId,
            attack_type: prediction.predicted_class,
            row_number: rowNumber,
            model_score: Number.isFinite(Number(prediction.model_score)) ? Number(prediction.model_score) : null,
            model_version: modelVersion,
            created_at: createdAt,
            verification_status: "model_generated_unverified",
          });
        }
      } else if (fieldValue && typeof fieldValue === "object" && !Array.isArray(fieldValue)) {
        visit(fieldValue, fieldPath, prediction, rowNumber);
      }
    }
  };
  for (const [index, prediction] of (predictions ?? []).entries()) {
    const attackType = typeof prediction?.predicted_class === "string" ? prediction.predicted_class.trim() : "";
    if (!attackType || attackType.toLowerCase() === "benign") continue;
    visit(prediction, "", prediction, prediction.row_number ?? index + 1);
  }
  return records;
}

export class MongoStore {
  constructor({ uri, databaseName }) {
    this.uri = uri;
    this.databaseName = databaseName;
    this.client = null;
    this.database = null;
    this.connected = false;
    this.error = null;
  }

  async connect() {
    if (!this.uri) {
      return;
    }
    try {
      this.client = new MongoClient(this.uri, { serverSelectionTimeoutMS: 1500 });
      await this.client.connect();
      this.database = this.client.db(this.databaseName);
      this.connected = true;
      this.error = null;
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
      this.connected = false;
    }
  }

  async persist(artifacts) {
    if (!this.connected) {
      return;
    }
    await this.database.collection("threat_summaries").replaceOne(
      { artifact_type: artifacts.summary.artifact_type },
      artifacts.summary,
      { upsert: true },
    );
    await this.database.collection("threat_events").createIndex(
      { threat_id: 1 },
      { unique: true },
    );
    if (artifacts.boundedEvents.length > 0) {
      await this.database.collection("threat_events").bulkWrite(
        artifacts.boundedEvents.map((event) => ({
          updateOne: {
            filter: { threat_id: event.threat_id },
            update: { $set: event },
            upsert: true,
          },
        })),
        { ordered: false },
      );
    }
  }

  async persistDetectionEvents(events) {
    if (!this.connected || events.length === 0) return;
    await this.database.collection("detection_events").createIndex(
      { event_id: 1 },
      { unique: true },
    );
    await this.database.collection("detection_events").bulkWrite(
      events.map((event) => ({
        updateOne: {
          filter: { event_id: event.event_id },
          update: { $set: event },
          upsert: true,
        },
      })),
      { ordered: false },
    );
  }

  async persistDetection(detection) {
    if (!this.connected) return false;
    const collection = this.database.collection("detections");
    await collection.createIndex({ detection_id: 1 }, { unique: true });
    await collection.createIndex({ created_at: 1 });
    await collection.replaceOne(
      { detection_id: detection.detection_id },
      detection,
      { upsert: true },
    );
    return true;
  }

  async persistCtiEvents({ detectionId, predictions, modelVersion, createdAt }) {
    if (!this.connected || !predictions?.length) return;
    const eventsByAttackType = new Map();
    for (const prediction of predictions) {
      const attackType = prediction.predicted_class;
      if (!attackType || attackType.toLowerCase() === "benign") continue;
      const score = Number(prediction.model_score);
      const current = eventsByAttackType.get(attackType) ?? {
        scores: [],
        predicted_count: 0,
      };
      current.predicted_count += 1;
      if (Number.isFinite(score)) current.scores.push(score);
      eventsByAttackType.set(attackType, current);
    }
    if (eventsByAttackType.size === 0) return;

    const collection = this.database.collection("cti_events");
    await collection.createIndex(
      { detection_id: 1, attack_type: 1 },
      { unique: true },
    );
    await collection.bulkWrite(
      [...eventsByAttackType.entries()].map(([attackType, values]) => {
        const scores = values.scores;
        return {
          updateOne: {
            filter: { detection_id: detectionId, attack_type: attackType },
            update: {
              $set: {
                event_id: `${detectionId}:${attackType}`,
                detection_id: detectionId,
                attack_type: attackType,
                predicted_count: values.predicted_count,
                average_model_score: scores.length
                  ? scores.reduce((sum, score) => sum + score, 0) / scores.length
                  : null,
                maximum_model_score: scores.length ? Math.max(...scores) : null,
                model_version: modelVersion,
                created_at: createdAt,
                verification_status: "model_generated_unverified",
              },
            },
            upsert: true,
          },
        };
      }),
      { ordered: false },
    );
  }

  async persistIocs({ detectionId, predictions, modelVersion, createdAt }) {
      if (!this.connected) return { saved: false, count: 0, status: "not_saved" };
      const records = extractIocs(predictions, detectionId, modelVersion, createdAt);
      if (!records.length) return { saved: false, count: 0, status: "empty" };
      const collection = this.database.collection("iocs");
      await collection.createIndex(
        { detection_id: 1, ioc_type: 1, normalized_value: 1, source_field: 1, row_number: 1 },
        { unique: true },
      );
      const result = await collection.bulkWrite(
        records.map((record) => ({
          updateOne: {
            filter: { ioc_id: record.ioc_id },
            update: { $set: record },
            upsert: true,
          },
        })),
        { ordered: false },
      );
      const count = (result.upsertedCount ?? 0) + (result.matchedCount ?? 0);
      return { saved: count > 0, count, status: count > 0 ? "saved" : "not_saved" };
    }

  async listIocs({ page, limit, search, iocType, attackType }) {
      if (!this.connected) throw new Error("MongoDB is not connected");
      const collection = this.database.collection("iocs");
      const query = { verification_status: "model_generated_unverified" };
      if (search) {
        const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        query.normalized_value = { $regex: escapedSearch, $options: "i" };
      }
      if (iocType) query.ioc_type = iocType;
      if (attackType) query.attack_type = attackType;
      const [total, iocs] = await Promise.all([
        collection.countDocuments(query),
        collection.find(query).sort({ created_at: -1 }).skip((page - 1) * limit).limit(limit).toArray(),
      ]);
      return { iocs, total };
    }

  async getIoc(iocId) {
      if (!this.connected) throw new Error("MongoDB is not connected");
      return this.database.collection("iocs").findOne({
        ioc_id: iocId,
        verification_status: "model_generated_unverified",
      });
    }

  async listCtiEvents(limit = 50) {
    if (!this.connected) {
      throw new Error("MongoDB is not connected");
    }
    const collection = this.database.collection("cti_events");
    const [events, total] = await Promise.all([
      collection.find({}).sort({ created_at: -1 }).limit(limit).toArray(),
      collection.countDocuments({}),
    ]);
    return { events, total };
  }

  async getCtiEvent(eventId) {
    if (!this.connected) {
      throw new Error("MongoDB is not connected");
    }
    return this.database.collection("cti_events").findOne({ event_id: eventId });
  }

  async listDetections({ page, limit, search, attackType }) {
    if (!this.connected) {
      throw new Error("MongoDB is not connected");
    }
    const collection = this.database.collection("detections");
    const query = {};
    if (search) {
      const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      query.$or = [
        { detection_id: { $regex: escapedSearch, $options: "i" } },
        { filename: { $regex: escapedSearch, $options: "i" } },
      ];
    }
    if (attackType) {
      query["summary.groups.attack_type"] = attackType;
    }

    const total = await collection.countDocuments(query);
    const detections = await collection
      .find(query, { projection: { predictions: 0 } })
      .sort({ created_at: -1 })
      .skip((page - 1) * limit)
      .limit(limit)
      .toArray();
    return { detections, total };
  }

  async getDetection(detectionId) {
    if (!this.connected) {
      throw new Error("MongoDB is not connected");
    }
    return this.database.collection("detections").findOne({
      detection_id: detectionId,
    });
  }

  status() {
    return {
      configured: Boolean(this.uri),
      connected: this.connected,
      error: this.error,
    };
  }

  async close() {
    await this.client?.close();
  }
}
