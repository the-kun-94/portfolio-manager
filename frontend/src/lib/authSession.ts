// Stateless signed session tokens for the login gate — no database, just
// an HMAC over an expiry timestamp. Written against Web Crypto (not Node's
// `crypto` module) so it works in both the Edge middleware and the Edge
// API routes that issue/verify it.

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

export async function makeSessionToken(secret: string, ttlSeconds: number): Promise<string> {
  const expires = Date.now() + ttlSeconds * 1000;
  const payload = String(expires);
  const sig = await hmac(secret, payload);
  return `${payload}.${sig}`;
}

export async function verifySessionToken(secret: string, token: string | undefined | null): Promise<boolean> {
  if (!token) return false;
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return false;
  if (Date.now() > Number(payload)) return false;
  const expected = await hmac(secret, payload);
  return timingSafeEqual(expected, sig);
}
