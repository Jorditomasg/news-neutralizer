/**
 * API client for communicating with the News Neutralizer backend.
 */

import { getSessionId, sessionHeaders } from "./session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export { getSessionId, sessionHeaders };

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API Error ${status}: ${body}`);
    this.name = "ApiError";
  }
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const res = await fetch(url, {
    headers: {
      ...sessionHeaders(),
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
