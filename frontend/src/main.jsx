import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3000/api";

async function loadDashboard() {
  const paths = ["health", "system/status", "operators", "experiments", "threats/summary"];
  const responses = await Promise.all(paths.map((path) => fetch(`${API_URL}/${path}`)));
  if (responses.some((response) => !response.ok)) throw new Error("The API returned an error.");
  const values = await Promise.all(responses.map((response) => response.json()));
  return Object.fromEntries(paths.map((path, index) => [path, values[index]]));
}

function Metric({ label, value }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function Experiment({ title, report }) {
  const metrics = report?.final_metrics ?? {};
  return (
    <section className="panel">
      <div className="panel-heading"><div><p className="eyebrow">{title}</p><h2>Five-round performance</h2></div><span className="badge">{report?.configuration?.rounds ?? 0} rounds</span></div>
      <div className="metrics">
        <Metric label="Accuracy" value={`${((metrics.accuracy ?? 0) * 100).toFixed(2)}%`} />
        <Metric label="Macro-F1" value={`${((metrics.macro_f1 ?? 0) * 100).toFixed(2)}%`} />
        <Metric label="Weighted-F1" value={`${((metrics.weighted_f1 ?? 0) * 100).toFixed(2)}%`} />
      </div>
      <div className="rounds">
        {(report?.rounds ?? []).map((round) => (
          <div className="round" key={round.round}><span>R{round.round}</span><div className="bar"><i style={{ width: `${(round.validation_metrics.accuracy ?? 0) * 100}%` }} /></div><b>{((round.validation_metrics.accuracy ?? 0) * 100).toFixed(1)}%</b></div>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { loadDashboard().then(setData).catch((reason) => setError(reason.message)); }, []);
  if (error) return <main className="shell"><div className="error"><h1>Dashboard unavailable</h1><p>{error}</p><p>Start the backend on port 3000 and refresh.</p></div></main>;
  if (!data) return <main className="shell"><div className="loading">Loading security telemetry…</div></main>;
  const centralized = data.experiments.centralized.results;
  const federated = data.experiments.federated;
  return (
    <main className="shell">
      <header className="topbar"><div className="brand"><span className="logo">FT</span><div><strong>Federated Threat Intel</strong><small>5G cybersecurity operations</small></div></div><div className="health"><span /> API {data.health.status} · {data["system/status"].federated.rounds} rounds</div></header>
      <section className="hero"><p className="eyebrow">Operational overview</p><h1>Collaborative defense, without centralized raw data.</h1><p className="subtitle">A research-grade view of the centralized baseline and four simulated telecom operators running Flower FedAvg.</p></section>
      <section className="grid overview"><div className="panel accent"><p className="eyebrow">Centralized baseline</p><h2>Random Forest</h2><div className="metrics"><Metric label="Accuracy" value={`${(centralized.metrics.accuracy * 100).toFixed(2)}%`} /><Metric label="Macro-F1" value={`${(centralized.metrics.macro_f1 * 100).toFixed(2)}%`} /></div></div><div className="panel"><p className="eyebrow">Federated model</p><h2>SGDClassifier · FedAvg</h2><div className="metrics"><Metric label="IID F1" value={`${(federated.iid.final_metrics.macro_f1 * 100).toFixed(2)}%`} /><Metric label="Non-IID F1" value={`${(federated.non_iid.final_metrics.macro_f1 * 100).toFixed(2)}%`} /></div></div></section>
      <section className="section"><div className="section-title"><p className="eyebrow">Federation topology</p><h2>Simulated operators</h2></div><div className="operators">{data.operators.operators.map((operator) => <article className="operator" key={operator.id}><div className="operator-head"><span className="node" /><h3>{operator.name}</h3><span className="status">{operator.status}</span></div><p>{operator.iid_rows.toLocaleString()} IID local records</p><small>{operator.non_iid_rows.toLocaleString()} non-IID · {operator.iid_classes} classes</small></article>)}</div></section>
      <section className="grid experiments"><Experiment title="IID federation" report={federated.iid} /><Experiment title="Non-IID federation" report={federated.non_iid} /></section>
      <section className="panel threat"><div className="panel-heading"><div><p className="eyebrow">Threat intelligence</p><h2>Detection events</h2></div><span className="badge muted">No events available</span></div><p>{data["threats/summary"].message}</p></section>
      <footer>Source: verified local experiment artifacts · In-process simulation · No raw operator records exposed</footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
