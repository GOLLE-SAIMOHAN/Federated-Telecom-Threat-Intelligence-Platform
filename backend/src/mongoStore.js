import { MongoClient } from "mongodb";

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
