import { locales } from "@/i18n/index";

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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Session-ID": getSessionId(),
  };

  if (typeof window !== "undefined") {
    // Resolve the ISO code from the locale registry (e.g. es_ES → "es", en_GB → "en")
    const localeKey = localStorage.getItem("app_locale");
    if (localeKey && localeKey in locales) {
      headers["Accept-Language"] = locales[localeKey as keyof typeof locales].iso;
    } else {
      // Backwards-compat: old key stored just "es" or "en"
      const oldLang = localStorage.getItem("app_lang");
      if (oldLang) headers["Accept-Language"] = oldLang;
    }

    const summaryLen = localStorage.getItem("app_summary_length");
    if (summaryLen) headers["X-Summary-Length"] = summaryLen;

    const biasStr = localStorage.getItem("app_bias_strictness");
    if (biasStr) headers["X-Bias-Strictness"] = biasStr;
  }

  return headers;
}
