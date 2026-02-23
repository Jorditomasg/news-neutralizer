"use client";

import { useState, useEffect } from "react";
import type { APIKeyInfo, AIProvider } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
import { sessionHeaders } from "@/lib/session";

const PROVIDERS: { id: AIProvider; name: string; description: string; keyPrefix: string }[] = [
  { id: "openai", name: "OpenAI", description: "GPT-4o, GPT-4o-mini", keyPrefix: "sk-" },
  { id: "anthropic", name: "Anthropic", description: "Claude 3.5 Sonnet", keyPrefix: "sk-ant-" },
  { id: "google", name: "Google AI", description: "Gemini 2.0 Flash", keyPrefix: "" },
  { id: "ollama", name: "Ollama (local)", description: "Llama 3.1, Mistral (sin API key)", keyPrefix: "" },
];

export default function SettingsPage() {
  const [keys, setKeys] = useState<APIKeyInfo[]>([]);
  const [saving, setSaving] = useState<string | null>(null);
  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings/api-keys`, { headers: sessionHeaders() });
      if (res.ok) {
        const data = await res.json();
        setKeys(data);
      }
    } catch (e) {
      console.error("Failed to fetch keys", e);
    }
  };

  const saveKey = async (provider: AIProvider) => {
    const value = inputValues[provider];
    if (!value?.trim()) return;

    setSaving(provider);
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings/api-keys`, {
        method: "POST",
        headers: sessionHeaders(),
        body: JSON.stringify({ provider, api_key: value.trim() }),
      });

      if (res.ok) {
        setFeedback({ ...feedback, [provider]: "✅ Guardada" });
        setInputValues({ ...inputValues, [provider]: "" });
        await fetchKeys();
      } else {
        setFeedback({ ...feedback, [provider]: "❌ Error al guardar" });
      }
    } catch (e) {
      setFeedback({ ...feedback, [provider]: "❌ Error de conexión" });
    } finally {
      setSaving(null);
      setTimeout(() => {
        setFeedback((prev) => {
          const next = { ...prev };
          delete next[provider];
          return next;
        });
      }, 3000);
    }
  };

  const deleteKey = async (provider: string) => {
    try {
      await fetch(`${API_BASE}/api/v1/settings/api-keys/${provider}`, {
        method: "DELETE",
        headers: sessionHeaders(),
      });
      await fetchKeys();
    } catch (e) {
      console.error("Failed to delete key", e);
    }
  };

  const hasKey = (provider: string) => keys.some((k) => k.provider === provider);

  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white transition-colors">Configuración</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400 transition-colors">
          Configura tus claves API para los proveedores de IA. Las claves se cifran antes de
          almacenarse.
        </p>
      </div>

      {/* Security Notice */}
      <div className="mb-8 rounded-2xl border border-teal-200 dark:border-teal-500/20 bg-teal-50 dark:bg-teal-500/5 p-4 transition-colors">
        <p className="text-sm text-teal-800 dark:text-teal-300 transition-colors">
          🔒 Tus claves API se cifran con Fernet (AES-128-CBC) y nunca se exponen en texto
          plano. Si no configuras ninguna clave, se usará Ollama local (gratis, sin API key).
        </p>
      </div>

      {/* Provider Cards */}
      <div className="space-y-4">
        {PROVIDERS.map((provider) => (
          <div
            key={provider.id}
            className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-5 shadow-sm dark:shadow-none transition-colors"
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-display font-semibold text-gray-900 dark:text-white transition-colors">
                  {provider.name}
                </h3>
                <p className="text-xs text-gray-500 transition-colors">{provider.description}</p>
              </div>
              {hasKey(provider.id) ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 rounded-lg px-2 py-1 transition-colors">
                    Configurada
                  </span>
                  <button
                    onClick={() => deleteKey(provider.id)}
                    className="text-xs text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300 transition-colors"
                  >
                    Eliminar
                  </button>
                </div>
              ) : (
                <span className="text-xs text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-white/5 rounded-lg px-2 py-1 transition-colors">
                  {provider.id === "ollama" ? "No requiere clave" : "No configurada"}
                </span>
              )}
            </div>

            {/* Input (only for providers that need keys) */}
            {provider.id !== "ollama" && (
              <div className="flex gap-2">
                <input
                  type="password"
                  value={inputValues[provider.id] || ""}
                  onChange={(e) =>
                    setInputValues({ ...inputValues, [provider.id]: e.target.value })
                  }
                  placeholder={`${provider.keyPrefix}...`}
                  className="flex-1 rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 outline-none focus:border-teal-400/50 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-400/20 transition-colors"
                />
                <button
                  onClick={() => saveKey(provider.id)}
                  disabled={!inputValues[provider.id]?.trim() || saving === provider.id}
                  className="rounded-xl bg-gray-100 dark:bg-white/5 px-4 py-2 text-sm text-gray-900 dark:text-white transition-colors hover:bg-gray-200 dark:hover:bg-white/10 disabled:opacity-30 border border-gray-200 dark:border-transparent"
                >
                  {saving === provider.id ? "..." : "Guardar"}
                </button>
              </div>
            )}

            {/* Feedback */}
            {feedback[provider.id] && (
              <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 transition-colors">{feedback[provider.id]}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
