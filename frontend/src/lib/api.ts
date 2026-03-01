/**
 * API client for communicating with the News Neutralizer backend.
 */

import { sessionHeaders } from "./session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SESSION_KEY = "news-neutralizer-session-id";

export { sessionHeaders };

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API Error ${status}: ${body}`);
    this.name = "ApiError";
  }
}

export async function getValidSessionToken(): Promise<string> {
  if (typeof window === "undefined") return "default";

  let token = localStorage.getItem(SESSION_KEY);
  
  // If no token exists, or if it looks like an old UUID (< 100 chars), fetch a JWT
  if (!token || token.length < 100) {
    const res = await fetch(`${API_BASE}/api/v1/auth/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old_session_id: token || undefined }),
    });
    if (res.ok) {
      const data = await res.json();
      token = data.access_token;
      if (token) {
        localStorage.setItem(SESSION_KEY, token);
      }
    }
  }
  return token || "default";
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  // Ensure we have a valid JWT before making the request
  const token = await getValidSessionToken();

  const res = await fetch(url, {
    headers: {
      ...sessionHeaders(),
      "X-Session-ID": token,
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  return res.json();
}

// ── Convenience methods ───────────────────────────────────────

export const api = {
  // Search
  search: (query: string, sources?: string[]) =>
    apiClient("/api/v1/search/", {
      method: "POST",
      body: JSON.stringify({ query, sources }),
    }),

  getSearchResults: (taskId: string) =>
    apiClient(`/api/v1/search/${taskId}`),

  crossReference: (articleId: number, topics: string[], sources?: string[]) =>
    apiClient("/api/v1/search/cross-reference", {
      method: "POST",
      body: JSON.stringify({ article_id: articleId, topics, sources }),
    }),

  // Articles
  extractArticle: (url: string) =>
    apiClient("/api/v1/articles/extract", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  // Settings
  saveApiKey: (provider: string, apiKey: string) =>
    apiClient("/api/v1/settings/api-keys", {
      method: "POST",
      body: JSON.stringify({ provider, api_key: apiKey }),
    }),

  listApiKeys: () => apiClient("/api/v1/settings/api-keys"),

  deleteApiKey: (provider: string) =>
    apiClient(`/api/v1/settings/api-keys/${provider}`, {
      method: "DELETE",
    }),

  // Sources
  listSources: () => apiClient("/api/v1/sources/"),
};
