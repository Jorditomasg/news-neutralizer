/**
 * Browser-side session management.
 * Generates a stable UUID per browser and stores it in localStorage.
 * This ID is sent as X-Session-ID on every API request to isolate
 * user data (API keys, history, feedback) without requiring auth.
 */

const SESSION_KEY = "news-neutralizer-session-id";

function generateUUID(): string {
  // Use crypto.randomUUID if available (modern browsers), else fallback
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers / SSR
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get the current session ID, creating one if it doesn't exist.
 * Returns "default" during SSR (no localStorage available).
 */
export function getSessionId(): string {
  if (typeof window === "undefined") return "default";

  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = generateUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/**
 * Returns common headers including the session ID.
 */
export function sessionHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-Session-ID": getSessionId(),
  };
}
