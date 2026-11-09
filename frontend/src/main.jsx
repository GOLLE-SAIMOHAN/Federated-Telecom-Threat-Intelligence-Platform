import React, { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3000/api";
const navigation = [
  ["overview", "Overview"],
  ["experiments", "Experiments"],
  ["operators", "Operators"],
  ["performance", "Model Performance"],
  ["workflow", "How It Works"],
  ["detection", "Intrusion Detection"],
  ["history", "Detection History"],
  ["threats", "Threat Intelligence"],
];
const workflowStages = [
  ["ingestion", "01", "5G-NIDD ingestion", "CSV telemetry is loaded through the existing inspection configuration.", "Python / pandas", "train_data.csv and test_data.csv"],
  ["preprocessing", "02", "Preprocessing and leakage removal", "Training-only fitting, missing-value handling, encoding, scaling and exact overlap removal protect evaluation integrity.", "scikit-learn Pipeline", "preprocessing.joblib and leakage report"],
  ["partitioning", "03", "IID and Non-IID partitions", "The cleaned training set is split into four reproducible operator partitions for both distribution strategies.", "NumPy / deterministic seed 42", "iid_operator_{a,b,c,d}.npz and non_iid_operator_{a,b,c,d}.npz"],
  ["baseline", "04", "Centralized Random Forest", "A centralized Random Forest provides the reference baseline. It is a separate experiment from federated SGD.", "RandomForestClassifier", "centralized_baseline_results.json"],
  ["clients", "05", "Four local federated clients", "Each simulated client trains on its own local partition and keeps feature and label arrays in-process.", "Flower NumPyClient", "four logical operator clients"],
  ["aggregation", "06", "Flower FedAvg across five rounds", "FedAvg combines model parameters weighted by client sample count; raw records are not sent as updates.", "Flower FedAvg", "federated_iid_rounds_5_report.json and federated_non_iid_rounds_5_report.json"],
  ["evaluation", "07", "Global model evaluation", "The final global model is evaluated against the untouched test artifact after round five.", "scikit-learn metrics", "final_metrics and confusion matrix"],
  ["dashboard", "08", "Results on this dashboard", "This interface reads the tracked demo snapshot derived from the verified experiment reports.", "Express API + React", "backend/data/demo-artifacts.json"],
];

async function loadDashboard() {
  const paths = ["health", "system/status", "operators", "experiments", "threats/summary"];
  const responses = await Promise.all(paths.map((path) => fetch(`${API_URL}/${path}`)));
  if (responses.some((response) => !response.ok)) throw new Error("The API returned an error.");
  const values = await Promise.all(responses.map((response) => response.json()));
  return Object.fromEntries(paths.map((path, index) => [path, values[index]]));
}

function Metric({ label, value, detail }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}

function SectionHeading({ eyebrow, title, action }) {
  return <div className="section-title"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{action}</div>;
}

function ConfusionMatrix({ matrix, labels }) {
  if (!matrix?.length) return <p className="muted-copy">No confusion matrix is available for this round.</p>;
  return (
    <div className="matrix-wrap">
      <table className="matrix"><thead><tr><th>Actual / Pred.</th>{labels.map((label) => <th key={label} title={label}>{label.slice(0, 7)}</th>)}</tr></thead>
        <tbody>{matrix.map((row, rowIndex) => <tr key={labels[rowIndex] ?? rowIndex}><th title={labels[rowIndex]}>{(labels[rowIndex] ?? `Class ${rowIndex}`).slice(0, 12)}</th>{row.map((value, colIndex) => <td className={value ? (rowIndex === colIndex ? "matrix-hit" : "matrix-miss") : ""} key={`${rowIndex}-${colIndex}`}>{value}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function RoundPanel({ report, labels }) {
  const [roundNumber, setRoundNumber] = useState(1);
  const round = report?.rounds?.find((item) => item.round === Number(roundNumber)) ?? report?.rounds?.[0];
  const metrics = round?.validation_metrics ?? {};
  return (
    <div className="panel round-panel">
      <div className="panel-heading"><div><p className="eyebrow">Local validation</p><h3>Round {round?.round ?? "-"} detail</h3></div>
        <label className="select-label">Round <select value={roundNumber} onChange={(event) => setRoundNumber(event.target.value)}>{(report?.rounds ?? []).map((item) => <option value={item.round} key={item.round}>{item.round}</option>)}</select></label>
      </div>
      <div className="metrics compact"><Metric label="Accuracy" value={`${((metrics.accuracy ?? 0) * 100).toFixed(2)}%`} /><Metric label="Macro-F1" value={`${((metrics.macro_f1 ?? 0) * 100).toFixed(2)}%`} /><Metric label="Weighted-F1" value={`${((metrics.weighted_f1 ?? 0) * 100).toFixed(2)}%`} /></div>
      <p className="muted-copy">{round?.validation_rows?.toLocaleString() ?? 0} validation rows aggregated from local confusion-matrix counts.</p>
      <ConfusionMatrix matrix={round?.validation_confusion_matrix} labels={labels} />
    </div>
  );
}

function ExperimentCard({ title, report, labels, expanded }) {
  const metrics = report?.final_metrics ?? {};
  return <article className="panel experiment-card"><div className="panel-heading"><div><p className="eyebrow">{title}</p><h3>{report?.configuration?.model?.split(".").pop() ?? "Federated model"}</h3></div><span className="badge">{report?.configuration?.rounds ?? 0} rounds</span></div>
    <div className="metrics"><Metric label="Accuracy" value={`${((metrics.accuracy ?? 0) * 100).toFixed(2)}%`} /><Metric label="Macro-F1" value={`${((metrics.macro_f1 ?? 0) * 100).toFixed(2)}%`} /><Metric label="Weighted-F1" value={`${((metrics.weighted_f1 ?? 0) * 100).toFixed(2)}%`} /></div>
    <div className="rounds">{(report?.rounds ?? []).map((round) => <div className="round" key={round.round}><span>R{round.round}</span><div className="bar"><i style={{ width: `${(round.validation_metrics.accuracy ?? 0) * 100}%` }} /></div><b>{((round.validation_metrics.accuracy ?? 0) * 100).toFixed(1)}%</b></div>)}</div>
    {expanded && <RoundPanel report={report} labels={labels} />}
  </article>;
}

function Operators({ operators }) {
  const [selected, setSelected] = useState(null);
  const current = operators.find((operator) => operator.id === selected);
  return <section id="operators" className="section"><SectionHeading eyebrow="Federation topology" title="Simulated operator clients" action={<span className="badge">4 clients · in-process simulation</span>} />
    <div className="operators">{operators.map((operator) => <button className={`operator ${selected === operator.id ? "selected" : ""}`} onClick={() => setSelected(operator.id)} key={operator.id}><div className="operator-head"><span className="node" /><h3>{operator.name}</h3><span className="status">{operator.status}</span></div><p>{operator.iid_rows.toLocaleString()} IID records</p><small>{operator.non_iid_rows.toLocaleString()} Non-IID · {operator.iid_classes} classes</small></button>)}</div>
    {current && <div className="panel operator-detail"><div><p className="eyebrow">Selected client</p><h3>{current.name}</h3><p>This is a logical telecom operator client, not an independently deployed service. Training data remains inside the client object during the in-process Flower simulation.</p></div><div className="detail-grid"><Metric label="IID partition" value={current.iid_rows.toLocaleString()} /><Metric label="Non-IID partition" value={current.non_iid_rows.toLocaleString()} /><Metric label="Classes" value={current.iid_classes} /></div><div className="callout">Client sends model parameters and scalar metrics to FedAvg, never raw feature arrays, labels or source indices.</div></div>}
  </section>;
}

function Workflow() {
  const [active, setActive] = useState(workflowStages[0][0]);
  const stage = workflowStages.find((item) => item[0] === active) ?? workflowStages[0];
  return <section id="workflow" className="section"><SectionHeading eyebrow="Research workflow" title="From telecom data to collaborative detection" /><div className="workflow-layout"><div className="workflow-list">{workflowStages.map((item) => <button className={`workflow-step ${active === item[0] ? "active" : ""}`} onClick={() => setActive(item[0])} key={item[0]}><b>{item[1]}</b><span>{item[2]}</span></button>)}</div><div className="panel workflow-detail"><p className="eyebrow">Stage {stage[1]}</p><h3>{stage[2]}</h3><p>{stage[3]}</p><div className="detail-row"><span>Technology</span><strong>{stage[4]}</strong></div><div className="detail-row"><span>Output / artifact</span><strong>{stage[5]}</strong></div></div></div><div className="architecture"><div className="arch-node">Operator A</div><div className="arch-node">Operator B</div><div className="arch-node">Operator C</div><div className="arch-node">Operator D</div><div className="arch-line" /><div className="arch-center"><strong>FedAvg coordinator</strong><small>5 communication rounds</small></div><div className="arch-arrow">Global model → local clients</div></div><p className="muted-copy privacy-note">Privacy boundary: raw records remain local to each simulated client. This is privacy-preserving parameter exchange in an in-process simulation, not independently isolated operator infrastructure.</p></section>;
}

function Performance({ centralized, iid, nonIid, labels }) {
  const rows = [["Centralized Random Forest", centralized?.metrics], ["Federated IID SGDClassifier", iid?.final_metrics], ["Federated Non-IID SGDClassifier", nonIid?.final_metrics]];
  const classRows = Object.entries(centralized?.per_class ?? {});
  return <section id="performance" className="section"><SectionHeading eyebrow="Model performance" title="Comparable experiment results" /><div className="comparison-table panel"><table><thead><tr><th>Experiment</th><th>Accuracy</th><th>Macro-F1</th><th>Weighted-F1</th></tr></thead><tbody>{rows.map(([name, metrics]) => <tr key={name}><th>{name}</th><td>{((metrics?.accuracy ?? 0) * 100).toFixed(2)}%</td><td>{((metrics?.macro_f1 ?? 0) * 100).toFixed(2)}%</td><td>{((metrics?.weighted_f1 ?? 0) * 100).toFixed(2)}%</td></tr>)}</tbody></table></div><div className="grid performance-grid"><div className="panel"><h3>Centralized per-class performance</h3><div className="class-list">{classRows.map(([name, metric]) => <div className="class-row" key={name}><span>{name}</span><div className="bar"><i style={{ width: `${(metric.f1 ?? 0) * 100}%` }} /></div><b>{((metric.f1 ?? 0) * 100).toFixed(1)}%</b></div>)}</div></div><div className="panel explanation"><h3>How to read these metrics</h3><p><strong>Accuracy</strong> is the share of all predictions that are correct. It can look high when benign examples dominate the dataset.</p><p><strong>Macro-F1</strong> averages F1 equally across classes, so rare attack classes matter as much as common classes.</p><p className="callout">Random Forest is the centralized baseline. Federated results use SGDClassifier with Flower FedAvg; they are separate model experiments, not identical-algorithm comparisons.</p></div></div></section>;
}

const requiredDetectionColumns = ["ip.len", "ip.flags.df", "ip.flags.mf", "tcp.port", "tcp.ack_raw", "ip.ttl", "ip.proto", "tcp.window_size.1", "tcp.ack", "tcp.seq", "tcp.len", "tcp.stream", "tcp.urgent_pointer", "tcp.flags", "tcp.analysis.ack_rtt", "http.request", "frame.time_relative", "frame.time_delta", "tcp.time_relative", "tcp.time_delta", "tcp.srcport", "tcp.dstport", "http.request.uri"];

function IntrusionDetection() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const selectFile = (event) => {
    const selected = event.target.files?.[0] ?? null;
    setResult(null);
    if (!selected) return;
    if (selected.size > 5 * 1024 * 1024) { setFile(null); setStatus("File exceeds the 5 MB upload limit."); return; }
    setFile(selected);
    const reader = new FileReader();
    reader.onload = () => {
      const headers = String(reader.result).split(/\r?\n/, 1)[0].split(",").map((value) => value.trim());
      const missing = requiredDetectionColumns.filter((column) => !headers.includes(column));
      setStatus(missing.length ? `Missing required columns: ${missing.join(", ")}` : "Schema looks valid. Ready for detection.");
    };
    reader.readAsText(selected.slice(0, 256 * 1024));
  };
  const detect = async () => {
    if (!file || status.startsWith("Missing") || status.startsWith("File")) return;
    setStatus("");
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/detection`, { method: "POST", headers: { "Content-Type": "text/csv" }, body: await file.text() });
      const body = await response.json();
      if (!response.ok) {
        const requestId = body.request_id || response.headers.get("X-Request-ID") || "Unavailable";
        throw new Error(`Error: ${body.error ?? "Detection failed."} | HTTP status: ${response.status} | Backend code: ${body.code ?? "Unavailable"} | Request ID: ${requestId}`);
      }
      setResult(body);
      setStatus("Detection completed.");
    } catch (error) { setStatus(error.message); } finally { setBusy(false); }
  };
  const download = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.predictions, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "intrusion-detection-results.json";
    link.click();
    URL.revokeObjectURL(link.href);
  };
  return <section id="detection" className="section"><SectionHeading eyebrow="Operational inference" title="Intrusion Detection" action={<span className="badge">Federated IID model</span>} />
    <div className="panel detection-panel"><input type="file" accept=".csv,text/csv" onChange={selectFile} /><p className="muted-copy">{file ? `${file.name} · ${(file.size / 1024).toFixed(1)} KB` : "Select a CSV containing the trained feature columns."}</p><p className={status.startsWith("Missing") || status.startsWith("File") || status.startsWith("Error:") ? "validation-error" : "validation-status"}>{status || "No file selected."}</p><button className="button" disabled={!file || busy || status.startsWith("Missing") || status.startsWith("File")} onClick={detect}>{busy ? "Processing..." : "Start detection"}</button>{result && <><div className="metrics detection-metrics"><Metric label="Processed" value={result.processed_rows.toLocaleString()} /><Metric label="Benign" value={result.benign_count.toLocaleString()} /><Metric label="Attacks" value={result.attack_count.toLocaleString()} /></div><div className="detection-summary">{result.summary.map((item) => <span key={item.predicted_class}>{item.predicted_class}: {item.count}</span>)}</div><div className="detection-results"><table><thead><tr><th>Row</th><th>Prediction</th><th>Score</th></tr></thead><tbody>{result.predictions.map((item) => <tr key={item.row_number}><td>{item.row_number}</td><td>{item.predicted_class}</td><td>{(item.model_score * 100).toFixed(2)}%</td></tr>)}</tbody></table></div><button className="button ghost" onClick={download}>Download prediction results</button></>}</div>
  </section>;
}

function DetectionHistory() {
  const [detections, setDetections] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [attackType, setAttackType] = useState("");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  const loadDetections = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page, limit: 10 });
      if (search.trim()) params.set("search", search.trim());
      if (attackType) params.set("attack_type", attackType);
      const response = await fetch(`${API_URL}/detections?${params}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.error ?? "Could not load detection history.");
      setDetections(body.detections ?? []);
      setTotal(body.total ?? 0);
      setTotalPages(body.pagination?.total_pages ?? 1);
    } catch (reason) {
      setError(reason.message);
      setDetections([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetections();
  }, [page, search, attackType]);

  const viewDetails = async (detectionId) => {
    setDetailLoading(true);
    setDetailError("");
    try {
      const response = await fetch(`${API_URL}/detections/${encodeURIComponent(detectionId)}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.error ?? "Could not load detection details.");
      setDetail(body);
    } catch (reason) {
      setDetailError(reason.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const attackTypes = [...new Set(detections.flatMap((detection) => (
    detection.summary?.groups ?? detection.summary ?? []
  ).map((group) => group.attack_type ?? group.predicted_class).filter(Boolean)))].sort();
  const summary = detail?.summary?.groups ?? detail?.summary ?? [];

  return <section id="history" className="section">
    <SectionHeading eyebrow="Saved inference results" title="Detection History" action={<button className="button ghost" onClick={loadDetections} disabled={loading}>{loading ? "Refreshing..." : "Refresh"}</button>} />
    {detail ? <div className="panel detection-detail">
      <div className="panel-heading"><div><p className="eyebrow">Detection details</p><h3>{detail.filename ?? detail.detection_id}</h3></div><button className="button ghost" onClick={() => setDetail(null)}>Back to history</button></div>
      <div className="detail-grid"><Metric label="Detection ID" value={detail.detection_id} /><Metric label="Timestamp" value={detail.created_at ? new Date(detail.created_at).toLocaleString() : "-"} /><Metric label="Model version" value={detail.model_version ?? "-"} /><Metric label="Processed" value={(detail.processed_rows ?? 0).toLocaleString()} /></div>
      {detailError && <p className="validation-error">{detailError}</p>}
      {detailLoading ? <p className="loading-copy">Loading detection details...</p> : <><h3>Summary</h3><div className="detection-summary">{summary.map((item, index) => <span key={`${item.attack_type ?? item.predicted_class}-${index}`}>{item.attack_type ?? item.predicted_class}: {item.count}</span>)}</div><div className="history-table"><table><thead><tr><th>Row</th><th>Prediction</th><th>Score</th></tr></thead><tbody>{(detail.predictions ?? []).map((item, index) => <tr key={item.row_number ?? index}><td>{item.row_number ?? "-"}</td><td>{item.predicted_class ?? item.attack_type ?? "-"}</td><td>{typeof item.model_score === "number" ? `${(item.model_score * 100).toFixed(2)}%` : "-"}</td></tr>)}</tbody></table></div></>}
    </div> : <><div className="history-controls"><input value={search} placeholder="Search detection ID or filename" onChange={(event) => { setSearch(event.target.value); setPage(1); }} /><select value={attackType} onChange={(event) => { setAttackType(event.target.value); setPage(1); }}><option value="">All attack types</option>{attackTypes.map((type) => <option value={type} key={type}>{type}</option>)}</select></div>
      {error && <div className="history-message error-copy">{error}</div>}
      {!error && loading ? <div className="history-message">Loading detection history...</div> : !error && !detections.length ? <div className="history-message">No saved detections found.</div> : !error && <div className="history-table panel"><table><thead><tr><th>Detection ID</th><th>Date and time</th><th>Filename</th><th>Processed records</th><th>Benign</th><th>Predicted attacks</th><th>Model version</th><th>Action</th></tr></thead><tbody>{detections.map((detection) => <tr key={detection.detection_id}><td>{detection.detection_id}</td><td>{detection.created_at ? new Date(detection.created_at).toLocaleString() : "-"}</td><td>{detection.filename ?? "-"}</td><td>{(detection.processed_rows ?? 0).toLocaleString()}</td><td>{(detection.benign_count ?? 0).toLocaleString()}</td><td>{(detection.attack_count ?? 0).toLocaleString()}</td><td>{detection.model_version ?? "-"}</td><td><button className="button ghost" onClick={() => viewDetails(detection.detection_id)}>View details</button></td></tr>)}</tbody></table></div>}
      <div className="history-pagination"><span>{total.toLocaleString()} saved record{total === 1 ? "" : "s"}</span><div><button className="button ghost" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Previous</button><span>Page {page} of {totalPages}</span><button className="button ghost" disabled={page >= totalPages || loading} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>
    </>}
  </section>;
}

function ThreatIntelligence() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [attackType, setAttackType] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadEvents = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/threats?limit=50`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.error ?? "Could not load threat intelligence records.");
      if (body.simulated_detection_events !== false) {
        throw new Error("Threat intelligence endpoint is not returning MongoDB CTI events.");
      }
      setEvents(Array.isArray(body.threats) ? body.threats : []);
      setTotal(Number.isInteger(body.total) ? body.total : body.threats?.length ?? 0);
      setSelected(null);
    } catch (reason) {
      setEvents([]);
      setTotal(0);
      setError(reason instanceof Error ? reason.message : "Could not load threat intelligence records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadEvents(); }, []);

  const attackTypes = [...new Set(events.map((event) => event.attack_type).filter(Boolean))].sort();
  const filteredEvents = events.filter((event) => {
    const matchesType = !attackType || event.attack_type === attackType;
    const query = search.trim().toLowerCase();
    return matchesType && (!query || `${event.attack_type ?? ""} ${event.detection_id ?? ""}`.toLowerCase().includes(query));
  });
  const detectionCount = new Set(events.map((event) => event.detection_id).filter(Boolean)).size;
  const unverifiedCount = events.filter((event) => event.verification_status === "model_generated_unverified").length;

  if (selected) {
    return <section id="threats" className="section">
      <SectionHeading eyebrow="Threat intelligence" title="Event details" action={<button className="button ghost" onClick={() => setSelected(null)}>Back to events</button>} />
      <div className="panel threat-detail">
        <div className="callout">Model-generated · Unverified</div>
        <dl className="threat-fields">{Object.entries(selected).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "-")}</dd></div>)}</dl>
      </div>
    </section>;
  }

  return <section id="threats" className="section">
    <SectionHeading eyebrow="Threat intelligence" title="MongoDB CTI events" action={<><span className="badge">Model-generated · Unverified</span><button className="button ghost" onClick={loadEvents} disabled={loading}>{loading ? "Refreshing..." : "Refresh"}</button></>} />
    {error ? <div className="history-message error-copy">{error}</div> : loading ? <div className="history-message">Loading MongoDB CTI events...</div> : <><div className="grid threat-metrics">
      <div className="panel"><Metric label="Total threat events" value={total.toLocaleString()} /></div>
      <div className="panel"><Metric label="Unique attack categories" value={attackTypes.length.toLocaleString()} /></div>
      <div className="panel"><Metric label="Detection records represented" value={detectionCount.toLocaleString()} /></div>
      <div className="panel"><Metric label="Unverified model-generated events" value={unverifiedCount.toLocaleString()} /></div>
    </div>
    {!events.length ? <div className="history-message">No MongoDB CTI events are available.</div> : <><div className="history-controls"><input value={search} placeholder="Search attack type or detection ID" onChange={(event) => setSearch(event.target.value)} /><select value={attackType} onChange={(event) => setAttackType(event.target.value)}><option value="">All attack types</option>{attackTypes.map((type) => <option value={type} key={type}>{type}</option>)}</select></div>
      {!filteredEvents.length ? <div className="history-message">No CTI events match the current filters.</div> : <div className="history-table panel"><table><thead><tr><th>Attack type</th><th>Predicted event count</th><th>Average model score</th><th>Maximum model score</th><th>Detection ID</th><th>Model version</th><th>Creation timestamp</th><th>Verification status</th><th>Action</th></tr></thead><tbody>{filteredEvents.map((event) => <tr key={event.event_id ?? `${event.detection_id}-${event.attack_type}`}><td>{event.attack_type ?? "-"}</td><td>{event.predicted_count ?? "-"}</td><td>{typeof event.average_model_score === "number" ? event.average_model_score.toFixed(4) : "-"}</td><td>{typeof event.maximum_model_score === "number" ? event.maximum_model_score.toFixed(4) : "-"}</td><td>{event.detection_id ?? "-"}</td><td>{event.model_version ?? "-"}</td><td>{event.created_at ? new Date(event.created_at).toLocaleString() : "-"}</td><td><span className="status">Model-generated · Unverified</span></td><td><button className="button ghost" onClick={() => setSelected(event)}>View details</button></td></tr>)}</tbody></table></div>}
    </>}</>}
  </section>;
}

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [activeSection, setActiveSection] = useState("overview");
  const [experimentMode, setExperimentMode] = useState("iid");
  const [loading, setLoading] = useState(true);
  const refresh = () => { setLoading(true); setError(""); loadDashboard().then(setData).catch((reason) => setError(reason.message)).finally(() => setLoading(false)); };
  useEffect(refresh, []);
  const labels = useMemo(() => Object.keys(data?.experiments?.centralized?.results?.per_class ?? {}), [data]);
  if (loading && !data) return <main className="shell"><div className="loading">Loading verified experiment telemetry...</div></main>;
  if (error && !data) return <main className="shell"><div className="error"><h1>Dashboard unavailable</h1><p>{error}</p><button className="button" onClick={refresh}>Retry</button></div></main>;
  const centralized = data.experiments.centralized.results;
  const federated = data.experiments.federated;
  const jump = (id) => { setActiveSection(id); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); };
  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="logo">FT</span><div><strong>Federated Threat Intel</strong><small>5G cybersecurity operations</small></div></div><div className="header-actions"><div className="health"><span /> API {data.health.status} · {data["system/status"].federated.rounds} rounds</div><button className="button ghost" onClick={refresh}>{loading ? "Refreshing..." : "Refresh data"}</button></div></header>
    <nav className="nav">{navigation.map(([id, label]) => <button className={activeSection === id ? "active" : ""} onClick={() => jump(id)} key={id}>{label}</button>)}</nav>
    <section id="overview" className="hero"><p className="eyebrow">Academic project demonstration</p><h1>Collaborative defense, without centralized raw data.</h1><p className="subtitle">Explore the verified centralized baseline, five-round Flower FedAvg experiments, simulated operator clients and the complete 5G threat-detection workflow.</p><div className="hero-actions"><button className="button" onClick={() => jump("experiments")}>Explore experiments</button><button className="button ghost" onClick={() => jump("workflow")}>How it works</button></div></section>
    <section className="grid overview-cards"><div className="panel accent"><p className="eyebrow">Centralized baseline</p><h2>Random Forest</h2><div className="metrics"><Metric label="Accuracy" value={`${(centralized.metrics.accuracy * 100).toFixed(2)}%`} /><Metric label="Macro-F1" value={`${(centralized.metrics.macro_f1 * 100).toFixed(2)}%`} /></div></div><div className="panel"><p className="eyebrow">Federated comparison</p><h2>SGDClassifier · FedAvg</h2><div className="metrics"><Metric label="IID F1" value={`${(federated.iid.final_metrics.macro_f1 * 100).toFixed(2)}%`} /><Metric label="Non-IID F1" value={`${(federated.non_iid.final_metrics.macro_f1 * 100).toFixed(2)}%`} /></div></div></section>
    <section id="experiments" className="section"><SectionHeading eyebrow="Experiment comparison" title="Five-round federation" action={<div className="segmented"><button className={experimentMode === "iid" ? "active" : ""} onClick={() => setExperimentMode("iid")}>IID detail</button><button className={experimentMode === "non_iid" ? "active" : ""} onClick={() => setExperimentMode("non_iid")}>Non-IID detail</button></div>} /><div className="experiment-grid"><ExperimentCard title="IID federation" report={federated.iid} labels={labels} expanded={experimentMode === "iid"} /><ExperimentCard title="Non-IID federation" report={federated.non_iid} labels={labels} expanded={experimentMode === "non_iid"} /></div></section>
    <Operators operators={data.operators.operators} />
    <Performance centralized={centralized} iid={federated.iid} nonIid={federated.non_iid} labels={labels} />
    <Workflow />
    <IntrusionDetection />
    <DetectionHistory />
    <ThreatIntelligence />
    <footer>Source: verified local experiment artifacts · In-process simulation · No raw operator records exposed</footer>
  </main>;
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
