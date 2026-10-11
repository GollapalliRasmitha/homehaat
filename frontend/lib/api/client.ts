/**
 * The one place that calls fetch(). Components never call fetch directly;
 * they call the typed functions in lib/api/*.ts, which call apiFetch().
 *
 * In the browser, requests go to /api/* on Next.js (same origin), which
 * proxies them to Django, so the httpOnly session cookie is sent automatically.
 * On the server (server components), we call Django directly.
 */

/** Turns any failed API reply into one short sentence a buyer or seller can understand. */
export function friendlyMessage(status: number, data: Record<string, unknown>): string {
  if (typeof data.detail === "string") return data.detail; // Django already wrote a message for people
  if (status === 0) return "Can't reach HomeHaat right now. Check your internet connection and try again.";
  if (status >= 500) return "Our server had a problem. Please try again in a moment.";
  if (status === 404) return "We couldn't find that. It may have been removed.";
  if (status === 429) return "Too many tries. Please wait a minute and try again.";
  // A form error such as {"name": ["This field is required."]}: show the first one.
  for (const value of Object.values(data)) {
    if (Array.isArray(value) && value.length) return String(value[0]);
  }
  return "Something went wrong. Please try again.";
}

export class ApiError extends Error {
  status: number; // 0 = no reply at all (offline, or the server is down)
  data: Record<string, unknown>;
  path: string;

  constructor(status: number, data: Record<string, unknown>, path = "") {
    super(friendlyMessage(status, data));
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    this.path = path;
  }

  /** First message for one form field, e.g. fieldError("pincode"). */
  fieldError(field: string): string | undefined {
    const value = this.data[field];
    return Array.isArray(value) ? String(value[0]) : undefined;
  }
}

/** The message to show for any error: friendly for API errors, a safe default for anything else. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

const isServer = typeof window === "undefined";
const BASE = isServer ? (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000") : "";

function readCookie(name: string): string | undefined {
  if (isServer) return undefined;
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(name + "="))
    ?.split("=")[1];
}

// Must match CSRF_COOKIE_NAME in backend/config/settings.py.
const CSRF_COOKIE = "homehaat_csrftoken";

let csrfReady: Promise<unknown> | null = null;

/** Django needs the CSRF cookie before any POST/PATCH/DELETE. */
async function ensureCsrf() {
  if (readCookie(CSRF_COOKIE)) return;
  csrfReady ??= fetch("/api/auth/csrf/", { credentials: "same-origin" });
  try {
    await csrfReady;
  } catch {
    throw new ApiError(0, {}, "/auth/csrf/"); // offline or server down
  } finally {
    csrfReady = null;
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

export async function apiFetch<T>(path: string, options: { method?: Method; body?: unknown } = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  if (method !== "GET") {
    await ensureCsrf();
    headers["X-CSRFToken"] = readCookie(CSRF_COOKIE) ?? "";
  }
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${BASE}/api${path}`, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "same-origin",
      cache: "no-store", // always fresh: stock and prices change
    });
  } catch {
    // No reply at all: offline, or Django isn't running. Report it like any other API error.
    throw new ApiError(0, {}, path);
  }

  // A crash page or a proxy error isn't JSON: treat it as "no details".
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(`API ${method} ${path} failed with ${response.status}`, data); // a clue for debugging
    }
    throw new ApiError(response.status, data, path);
  }
  return data as T;
}
