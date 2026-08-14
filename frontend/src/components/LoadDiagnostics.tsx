import { useSyncExternalStore, useState } from "react";
import { subscribeTrace, getTraceSnapshot, type TraceEntry } from "../lib/loadTrace";

function statusIcon(status: TraceEntry["status"]): string {
  switch (status) {
    case "ok":
      return "✓";
    case "error":
      return "✕";
    case "retrying":
      return "↻";
    default:
      return "…";
  }
}

function statusClass(status: TraceEntry["status"]): string {
  switch (status) {
    case "ok":
      return "trace-ok";
    case "error":
      return "trace-error";
    case "retrying":
      return "trace-retrying";
    default:
      return "trace-pending";
  }
}

function formatDuration(entry: TraceEntry): string {
  const ms = entry.durationMs ?? Date.now() - entry.startedAt;
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

export default function LoadDiagnostics() {
  const entries = useSyncExternalStore(subscribeTrace, getTraceSnapshot, getTraceSnapshot);
  const [expanded, setExpanded] = useState(false);

  if (entries.length === 0) return null;

  const waking = entries.some((e) => e.status === "retrying" || (e.status === "pending" && e.attempt > 1));
  const inFlight = entries.some((e) => e.status === "pending" || e.status === "retrying");
  const failed = entries.filter((e) => e.status === "error" && e.attempt >= 1 && !inFlight);

  return (
    <div className="load-diagnostics">
      <button className="load-diagnostics-toggle" onClick={() => setExpanded((v) => !v)}>
        <span className={`trace-summary-dot ${waking ? "trace-retrying" : failed.length ? "trace-error" : "trace-ok"}`} />
        {waking
          ? "Waking up the Engine — this can take up to a minute on the first load…"
          : `Load trace (${entries.length} call${entries.length === 1 ? "" : "s"})`}
        <span className="load-diagnostics-caret">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded ? (
        <ul className="load-diagnostics-list">
          {entries.map((entry) => (
            <li key={entry.key} className={`load-diagnostics-row ${statusClass(entry.status)}`}>
              <span className="trace-icon">{statusIcon(entry.status)}</span>
              <span className="trace-path">
                {entry.method} {entry.path}
              </span>
              {entry.attempt > 1 ? <span className="trace-attempt">attempt {entry.attempt}</span> : null}
              <span className="trace-duration">{formatDuration(entry)}</span>
              {entry.detail ? <span className="trace-detail">{entry.detail}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
