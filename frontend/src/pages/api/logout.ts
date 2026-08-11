export const config = { runtime: "edge" };

export default async function handler(): Promise<Response> {
  const cookie = ["session=", "HttpOnly", "Secure", "SameSite=Lax", "Path=/", "Max-Age=0"].join("; ");
  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { "Content-Type": "application/json", "Set-Cookie": cookie },
  });
}
