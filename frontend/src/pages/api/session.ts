// Lets the client know its own session role (write/read/none) so the UI
// can disable trade/park controls for a read-only visitor — cosmetic only,
// the real enforcement is server-side in proxy/[...path].ts and the
// backend's require_write_access.
export const config = { runtime: "edge" };

import { verifySessionToken, getCookie } from "../../lib/authSession";

const SESSION_SECRET = process.env.SESSION_SECRET || "";

export default async function handler(req: Request): Promise<Response> {
  // Mirrors the dev bypass in middleware.ts / proxy/[...path].ts.
  if (!SESSION_SECRET) {
    return new Response(JSON.stringify({ role: "write" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const token = getCookie(req, "session");
  const role = await verifySessionToken(SESSION_SECRET, token);
  return new Response(JSON.stringify({ role }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
