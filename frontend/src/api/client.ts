import { useAuthStore } from "../store/authStore";
import type { AccessToken, ApiErrorBody } from "./types";

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody | null;

  constructor(status: number, message: string, body: ApiErrorBody | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function extractErrorMessage(body: ApiErrorBody | null, fallback: string): string {
  if (!body?.detail) return fallback;
  if (typeof body.detail === "string") return body.detail;
  return body.detail.map((item) => item.msg).join(", ");
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setAccessToken, logout } = useAuthStore.getState();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) {
          logout();
          return null;
        }
        const data = (await response.json()) as AccessToken;
        setAccessToken(data.access_token);
        return data.access_token;
      } catch {
        logout();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export interface ApiFetchOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | string[] | undefined>;
  skipAuth?: boolean;
}

function buildQueryString(query: ApiFetchOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, item);
    } else {
      params.append(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/** Client fetch typed, avec injection du token et retry automatique sur 401
 * (un seul essai de refresh, pour eviter une boucle infinie). */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = "GET", body, query, skipAuth = false } = options;
  const url = `/api/v1${path}${buildQueryString(query)}`;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (!skipAuth) {
      const token = useAuthStore.getState().accessToken;
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    return fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await doFetch();

  if (response.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await doFetch();
    }
  }

  if (!response.ok) {
    const errorBody = (await parseJsonSafe(response)) as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      extractErrorMessage(errorBody, `Erreur ${response.status}`),
      errorBody,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
