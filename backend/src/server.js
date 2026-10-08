import "dotenv/config";
import { createApp } from "./app.js";
import { loadArtifacts } from "./artifactStore.js";
import { MongoStore } from "./mongoStore.js";

const port = Number(process.env.BACKEND_PORT ?? 3000);
const artifacts = await loadArtifacts();
const mongoStore = new MongoStore({
  uri: process.env.MONGODB_URI,
  databaseName: process.env.MONGODB_DATABASE ?? "federated_telecom",
});
await mongoStore.connect();
await mongoStore.persist(artifacts);

const server = createApp({ artifacts, mongoStore }).listen(port, () => {
  console.log(`Backend listening on port ${port}`);
});

async function shutdown() {
  server.close();
  await mongoStore.close();
}

process.once("SIGINT", shutdown);
process.once("SIGTERM", shutdown);
