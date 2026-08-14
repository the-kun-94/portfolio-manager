// Lightweight, framework-agnostic trace of the dashboard's outbound API
// calls — what's being requested, how many attempts it took, and how long
// each attempt ran. Exists so a cold Render backend (spins down after 15
// min idle, takes 30-60s to wake) is visible as "retrying, Nth attempt"
// instead of a silent hang followed by an opaque error.
export type TraceStatus = "pending" | "retrying" | "ok" | "error";

export interface TraceEntry {
  key: string;
  method: string;
  path: string;
  status: TraceStatus;
  attempt: number;
  startedAt: number;
  updatedAt: number;
  durationMs: number | null;
  detail: string | null;
}

type Listener = () => void;

const entries = new Map<string, TraceEntry>();
const listeners = new Set<Listener>();
let snapshot: TraceEntry[] = [];

function publish(): void {
  snapshot = Array.from(entries.values()).sort((a, b) => a.startedAt - b.startedAt);
  listeners.forEach((listener) => listener());
}

export function resetTrace(): void {
  entries.clear();
  publish();
}

export function traceStart(method: string, path: string, attempt: number): void {
  const key = `${method} ${path}`;
  const now = Date.now();
  const existing = entries.get(key);
  entries.set(key, {
    key,
    method,
    path,
    status: attempt > 1 ? "retrying" : "pending",
    attempt,
    startedAt: existing?.startedAt ?? now,
    updatedAt: now,
    durationMs: null,
    detail: null,
  });
  publish();
}

export function traceSettle(method: string, path: string, status: "ok" | "error", detail: string | null): void {
  const key = `${method} ${path}`;
  const existing = entries.get(key);
  if (!existing) return;
  entries.set(key, {
    ...existing,
    status,
    updatedAt: Date.now(),
    durationMs: Date.now() - existing.startedAt,
    detail,
  });
  publish();
}

export function subscribeTrace(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getTraceSnapshot(): TraceEntry[] {
  return snapshot;
}
