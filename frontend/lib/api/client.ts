/**
 * The one place that calls fetch(). Components never call fetch directly;
 * they call the typed functions in lib/api/*.ts, which call apiFetch().
 *
 * In the browser, requests go to /api/* on Next.js (same origin), which
 * proxies them to Django, so the httpOnly session cookie is sent automatically.
 * On the server (server components), we call Django directly.
 */

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(status: number, data: Record<string, unknown>) {
    super(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
    this.status = status;
    this.data = data;
  }

  /** First message for one form field, e.g. fieldError("pincode"). */
  fieldError(field: string): string | undefined {
    const value = this.data[field];
    return Array.isArray(value) ? String(value[0]) : undefined;
  }
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

let csrfReady: Promise<unknown> | null = null;

/** Django needs the csrftoken cookie before any POST/PATCH/DELETE. */
async function ensureCsrf() {
  if (readCookie("csrftoken")) return;
  csrfReady ??= fetch("/api/auth/csrf/", { credentials: "same-origin" });
  await csrfReady;
  csrfReady = null;
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

export async function apiFetch<T>(path: string, options: { method?: Method; body?: unknown } = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  if (method !== "GET") {
    await ensureCsrf();
    headers["X-CSRFToken"] = readCookie("csrftoken") ?? "";
  }
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "same-origin",
    cache: "no-store", // always fresh: stock and prices change
  });

  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}
