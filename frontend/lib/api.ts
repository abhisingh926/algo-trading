import type { ApiEnvelope, ValidationErrorItem } from "@/types";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");
export const API_PREFIX = "/api/v1";

const TOKEN_KEY = "algo.access_token";

const tokenListeners = new Set<() => void>();
function emitTokenChange(): void {
  tokenListeners.forEach((l) => l());
}

export const tokenStore = {
  subscribe(listener: () => void): () => void {
    tokenListeners.add(listener);
    window.addEventListener("storage", listener);
    return () => {
      tokenListeners.delete(listener);
      window.removeEventListener("storage", listener);
    };
  },
  get(): string | null {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string): void {
    try {
      window.localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable */
    }
    emitTokenChange();
  },
  clear(): void {
    try {
      window.localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
    emitTokenChange();
  },
};

export class ApiError extends Error {
  readonly code: number;
  readonly description: string;
  readonly data: unknown;

  constructor(message: string, code: number, description: string, data: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.description = description;
    this.data = data;
  }

  /** Field level errors from a 422 response, if any. */
  get fieldErrors(): ValidationErrorItem[] {
    const d = this.data;
    if (d && typeof d === "object" && "errors" in d) {
      const errors = (d as { errors: unknown }).errors;
      if (Array.isArray(errors)) {
        return errors.filter(
          (e): e is ValidationErrorItem =>
            !!e && typeof e === "object" && "field" in e && "message" in e,
        );
      }
    }
    return [];
  }
}

type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  query?: object;
  body?: unknown;
  signal?: AbortSignal;
  /** Set to false for endpoints that are not under /api/v1 (e.g. /health). */
  prefixed?: boolean;
}

function buildUrl(path: string, query?: object, prefixed = true): string {
  const url = `${API_BASE_URL}${prefixed ? API_PREFIX : ""}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query as Record<string, QueryValue>)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

function isEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return (
    !!value &&
    typeof value === "object" &&
    "success" in value &&
    "status" in value &&
    "data" in value
  );
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", query, body, signal, prefixed = true } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query, prefixed), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(
      "Cannot reach the trading backend",
      0,
      `Network error while calling ${API_BASE_URL}. Check that the backend is running.`,
      null,
    );
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (response.status === 401) {
    // Clearing the token notifies the auth provider, which redirects to /login.
    tokenStore.clear();
  }

  if (isEnvelope(payload)) {
    if (!response.ok || !payload.success) {
      throw new ApiError(
        payload.message || "Request failed",
        payload.status?.code ?? response.status,
        payload.status?.description ?? response.statusText,
        payload.data,
      );
    }
    return payload.data as T;
  }

  throw new ApiError(
    response.ok ? "Unexpected response from backend" : "Request failed",
    response.status,
    response.statusText || "Response was not a valid API envelope",
    payload,
  );
}

export const api = {
  get: <T>(path: string, query?: object, signal?: AbortSignal) =>
    request<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
