import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Runs before every /api request is forwarded to Django (next.config.ts rewrites).
 *
 * Django sees every request coming from this Next.js server, so on its own it can't tell visitors apart (the
 * sign-in rate limit would be shared by everyone). Here we pass on the visitor's IP, with PROXY_SECRET so Django
 * knows the header came from us and not from someone faking it (backend/core/client_ip.py).
 *
 * The visitor's IP comes from the hosting platform's x-real-ip / x-forwarded-for headers, which it sets itself
 * (on Vercel these can't be faked by the browser). Locally there's no secret and nothing is added.
 */
export function proxy(request: NextRequest) {
  const secret = process.env.PROXY_SECRET;
  if (!secret) return NextResponse.next();

  const headers = new Headers(request.headers);
  const ip = request.headers.get("x-real-ip") || request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "";
  headers.delete("x-homehaat-client-ip"); // never pass on a value the browser sent itself
  headers.delete("x-homehaat-proxy-secret");
  if (ip) {
    headers.set("x-homehaat-client-ip", ip);
    headers.set("x-homehaat-proxy-secret", secret);
  }
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };
