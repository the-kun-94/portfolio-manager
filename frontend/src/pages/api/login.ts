// Edge runtime — Web Crypto (not Node's `crypto`) is what authSession.ts uses.
export const config = { runtime: "edge" };

import { makeSessionToken, timingSafeEqual, type Role } from "../../lib/authSession";

const SITE_PASSWORD = process.env.SITE_PASSWORD || "";
// Optional: a second password that logs in with read-only access instead
// of the full write-capable session — see lib/authSession.ts and
// pages/api/proxy/[...path].ts for how that's enforced. Leave unset to
// not offer a read-only login at all.
const SITE_PASSWORD_READONLY = process.env.SITE_PASSWORD_READONLY || "";
const SESSION_SECRET = process.env.SESSION_SECRET || "";
// Server-side ceiling the signed token itself expires at, independent of
// the cookie's browser-close lifetime below — belt and suspenders.
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

  let role: Role | null = null;
  if (timingSafeEqual(password, SITE_PASSWORD)) {
    role = "write";
  } else if (SITE_PASSWORD_READONLY && timingSafeEqual(password, SITE_PASSWORD_READONLY)) {
    role = "read";
  }

  if (!role) {
    return new Response(JSON.stringify({ error: "Incorrect password." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const token = await makeSessionToken(SESSION_SECRET, SESSION_TTL_SECONDS, role);
  // No Max-Age/Expires — a browser-session cookie, cleared when the
  // browser fully closes (not just the tab). The token's own expiry above
  // is the server-side fallback for browsers that keep it around anyway.
  const cookie = [`session=${token}`, "HttpOnly", "Secure", "SameSite=Lax", "Path=/"].join("; ");

  return new Response(JSON.stringify({ ok: true, role }), {
    status: 200,
    headers: { "Content-Type": "application/json", "Set-Cookie": cookie },
  });
}
