// Edge runtime — Web Crypto (not Node's `crypto`) is what authSession.ts uses.
export const config = { runtime: "edge" };

import { makeSessionToken, timingSafeEqual } from "../../lib/authSession";

const SITE_PASSWORD = process.env.SITE_PASSWORD || "";
const SESSION_SECRET = process.env.SESSION_SECRET || "";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!SITE_PASSWORD || !SESSION_SECRET) {
    return new Response(
      JSON.stringify({ error: "Login is not configured on the server." }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  const body = await req.json().catch(() => ({}));
  const password = typeof body?.password === "string" ? body.password : "";

  if (!timingSafeEqual(password, SITE_PASSWORD)) {
    return new Response(JSON.stringify({ error: "Incorrect password." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const token = await makeSessionToken(SESSION_SECRET, SESSION_TTL_SECONDS);
  const cookie = [
    `session=${token}`,
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
    "Path=/",
    `Max-Age=${SESSION_TTL_SECONDS}`,
  ].join("; ");

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { "Content-Type": "application/json", "Set-Cookie": cookie },
  });
}
