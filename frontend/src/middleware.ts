import { NextRequest, NextResponse } from "next/server";
import { verifySessionToken } from "./lib/authSession";

// Empty in local dev (no SESSION_SECRET configured) disables the gate so
// `npm run dev` needs no extra setup. Set it in production.
const SESSION_SECRET = process.env.SESSION_SECRET || "";

export async function middleware(req: NextRequest) {
  if (!SESSION_SECRET) {
    return NextResponse.next();
  }

  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/api/login")) {
    return NextResponse.next();
  }

  const token = req.cookies.get("session")?.value;
  const role = await verifySessionToken(SESSION_SECRET, token);
  if (!role) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
