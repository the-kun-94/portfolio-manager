// Stateless signed session tokens for the login gate — no database, just
// an HMAC over an expiry timestamp + role. Written against Web Crypto (not
// Node's `crypto` module) so it works in both the Edge middleware and the
// Edge API routes that issue/verify it.

export type Role = "write" | "read";

function bufToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function hmac(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  return bufToHex(sig);
}

// Not cryptographically necessary for a single-user password gate, but
// cheap insurance against timing attacks on the password/signature compare.
export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

export async function makeSessionToken(secret: string, ttlSeconds: number, role: Role): Promise<string> {
  const expires = Date.now() + ttlSeconds * 1000;
  const payload = `${expires}.${role}`;
  const sig = await hmac(secret, payload);
  return `${payload}.${sig}`;
}

// Returns the token's role once verified (signature valid, not expired,
// role recognized), or null if the token is missing/tampered/expired.
export async function verifySessionToken(secret: string, token: string | undefined | null): Promise<Role | null> {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [expiresStr, role, sig] = parts;
  if (role !== "write" && role !== "read") return null;
  if (Date.now() > Number(expiresStr)) return null;
  const payload = `${expiresStr}.${role}`;
  const expected = await hmac(secret, payload);
  if (!timingSafeEqual(expected, sig)) return null;
  return role;
}

// Edge API routes (plain Web `Request`) don't get NextApiRequest's
// req.cookies helper, so this parses the `Cookie` header by hand.
export function getCookie(req: Request, name: string): string | undefined {
  const header = req.headers.get("cookie");
  if (!header) return undefined;
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq).trim() === name) {
      return part.slice(eq + 1).trim();
    }
  }
  return undefined;
}
