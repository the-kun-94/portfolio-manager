// Edge runtime — same reason as login.ts (Web Crypto for the session
// token) plus `fetch` for forwarding to the backend.
export const config = { runtime: "edge" };

import { verifySessionToken, getCookie, type Role } from "../../../lib/authSession";

const SESSION_SECRET = process.env.SESSION_SECRET || "";
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
// Deliberately NOT NEXT_PUBLIC_* — these must never reach the browser
// bundle. The old NEXT_PUBLIC_API_KEY approach meant every visitor's
// bundle carried the one key capable of executing trades; this proxy is
// what lets a read-only session exist at all, by keeping both keys
// server-side and picking the right one per request based on the
// session's role instead of the client attaching one itself.
const BACKEND_API_KEY_WRITE = process.env.API_KEY || "";
const BACKEND_API_KEY_READONLY = process.env.API_KEY_READONLY || "";

const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export default async function handler(req: Request): Promise<Response> {
  // Mirrors middleware.ts's dev bypass: no SESSION_SECRET configured means
  // the login gate is off entirely (local dev, zero config), so every
  // request gets full access, same as before this proxy existed.
  let role: Role = "write";

  if (SESSION_SECRET) {
    const token = getCookie(req, "session");
    const verified = await verifySessionToken(SESSION_SECRET, token);
    if (!verified) {
      return jsonResponse(401, { detail: "Not authenticated." });
    }
    role = verified;
  }

  if (role !== "write" && WRITE_METHODS.has(req.method)) {
    return jsonResponse(403, { detail: "Read-only session cannot perform write actions." });
  }

  const url = new URL(req.url);
  const backendPath = url.pathname.replace(/^\/api\/proxy/, "");
  const backendUrl = `${BACKEND_BASE_URL}${backendPath}${url.search}`;

  const apiKey = role === "write" ? BACKEND_API_KEY_WRITE : BACKEND_API_KEY_READONLY;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;

  const hasBody = WRITE_METHODS.has(req.method);

  let backendRes: Response;
  try {
    backendRes = await fetch(backendUrl, {
      method: req.method,
      headers,
      body: hasBody ? await req.text() : undefined,
    });
  } catch {
    return jsonResponse(502, {
      detail: `Could not reach the Engine at ${BACKEND_BASE_URL}. Is it running?`,
    });
  }

  const responseBody = await backendRes.text();
  return new Response(responseBody, {
    status: backendRes.status,
    headers: { "Content-Type": backendRes.headers.get("content-type") || "application/json" },
  });
}
