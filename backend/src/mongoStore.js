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
