"use client";

import { useState, useEffect } from "react";
import type { APIKeyInfo, AIProvider } from "@/types";
import { sessionHeaders } from "@/lib/session";
import { useI18n } from "@/context/I18nContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PROVIDERS: { id: AIProvider; keyPrefix: string }[] = [
  { id: "openai", keyPrefix: "sk-" },
  { id: "anthropic", keyPrefix: "sk-ant-" },
  { id: "google", keyPrefix: "" },
  { id: "ollama", keyPrefix: "" },
];

export default function SettingsPage() {
  const { t, locale, setLocale, availableLanguages, summaryLength, setSummaryLength, biasStrictness, setBiasStrictness } = useI18n();
  const [keys, setKeys] = useState<APIKeyInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [activeProvider, setActiveProvider] = useState<AIProvider>("ollama");
  const [inputValue, setInputValue] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings/api-keys`, { headers: sessionHeaders() });
      if (res.ok) {
        const data: APIKeyInfo[] = await res.json();
        setKeys(data);
        if (data.length > 0) {
          setActiveProvider(data[0].provider);
        } else {
          setActiveProvider("ollama");
        }
      }
    } catch (e) {
      console.error("Failed to fetch keys", e);
    }
  };

  const saveKey = async () => {
    // If Ollama is selected, we just delete all other keys to enforce it as the active provider.
    // If another is selected, we save its key.
    
    // In our backend implementation (which we'll do next), saving a new key will delete others.
    // But if we're switching to Ollama, we need an explicit endpoint or we can just delete the active key.
    setSaving(true);
    setFeedback("");

    try {
      if (activeProvider === "ollama") {
        // Delete all keys to default to ollama
        for (const k of keys) {
          await fetch(`${API_BASE}/api/v1/settings/api-keys/${k.provider}`, {
            method: "DELETE",
            headers: sessionHeaders(),
          });
        }
        setFeedback(t?.prefs.saved);
        setInputValue("");
        await fetchKeys();
      } else {
        if (!inputValue.trim()) {
           setSaving(false);
           return;
        }
        
        const res = await fetch(`${API_BASE}/api/v1/settings/api-keys`, {
          method: "POST",
          headers: sessionHeaders(),
          body: JSON.stringify({ provider: activeProvider, api_key: inputValue.trim() }),
        });

        if (res.ok) {
          setFeedback(t?.prefs.saved);
          setInputValue("");
          await fetchKeys();
        } else {
          setFeedback(t?.prefs.error);
        }
      }
    } catch (e) {
      setFeedback(t?.prefs.error);
    } finally {
      setSaving(false);
      setTimeout(() => setFeedback(""), 3000);
    }
  };

  const getProviderName = (id: AIProvider) => {
    return t?.settings.provider[id as keyof typeof t?.settings.provider] || id;
  };
  
  const getProviderDesc = (id: AIProvider) => {
    return t?.settings.provider[`${id}_desc` as keyof typeof t?.settings.provider] || "";
  };
  
  const selectedProviderConf = PROVIDERS.find(p => p.id === activeProvider);
  const isKeySavedForProvider = keys.some(k => k.provider === activeProvider);

  return (
    <div className="animate-fade-in max-w-2xl mx-auto space-y-10">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white">{t?.settings.title}</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">{t?.settings.description}</p>
      </div>

      {/* Preferences Section */}
      <section className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">{t?.prefs.preferences}</h2>
          <p className="text-sm text-gray-600 dark:text-gray-500">{t?.prefs.preferences_desc}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Language Selector */}
          <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-5 shadow-sm dark:shadow-none">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{t?.prefs.language}</label>
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as Parameters<typeof setLocale>[0])}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2.5 text-sm text-gray-900 dark:text-white outline-none focus:border-teal-500/40 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-500/20 transition-colors"
            >
              {availableLanguages.map((lang) => (
                <option key={lang.key} value={lang.key} className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">
                  {lang.flag} {lang.label}
                </option>
              ))}
            </select>
          </div>

          {/* AI Provider Selector */}
          <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-5 shadow-sm dark:shadow-none">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{t?.prefs.ai_model}</label>
            <select
              value={activeProvider}
              onChange={(e) => {
                const newProv = e.target.value as AIProvider;
                setActiveProvider(newProv);
                setInputValue(""); 
              }}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2.5 text-sm text-gray-900 dark:text-white outline-none focus:border-teal-500/40 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-500/20 transition-colors"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id} className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">
                  {getProviderName(p.id)}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-2">
              {getProviderDesc(activeProvider)}
            </p>
          </div>

          {/* Summary Length Selector */}
          <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-5 shadow-sm dark:shadow-none">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{t?.prefs.summaryLength}</label>
            <select
              value={summaryLength}
              onChange={(e) => setSummaryLength(e.target.value)}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2.5 text-sm text-gray-900 dark:text-white outline-none focus:border-teal-500/40 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-500/20 transition-colors"
            >
              <option value="short" className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">{t?.prefs.summaryLength_short}</option>
              <option value="medium" className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">{t?.prefs.summaryLength_medium}</option>
              <option value="long" className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">{t?.prefs.summaryLength_long}</option>
            </select>
          </div>

          {/* Bias Strictness Selector */}
          <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-5 shadow-sm dark:shadow-none">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{t?.prefs.biasStrictness}</label>
            <select
              value={biasStrictness}
              onChange={(e) => setBiasStrictness(e.target.value)}
              className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2.5 text-sm text-gray-900 dark:text-white outline-none focus:border-teal-500/40 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-500/20 transition-colors"
            >
              <option value="standard" className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">{t?.prefs.biasStrictness_standard}</option>
              <option value="strict" className="bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-white">{t?.prefs.biasStrictness_strict}</option>
            </select>
          </div>
        </div>
      </section>

      {/* Security Notice */}
      <div className="rounded-2xl border border-teal-200 dark:border-teal-500/20 bg-teal-50 dark:bg-teal-500/5 p-4">
        <p className="text-sm text-teal-800 dark:text-teal-300">
          {t?.settings.securityNotice}
        </p>
      </div>

      {/* API Key Input Section (Conditional) */}
      <section className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-6 shadow-sm dark:shadow-none">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900 dark:text-white">{t?.prefs.provider}: {getProviderName(activeProvider)}</h3>
          {isKeySavedForProvider && activeProvider !== "ollama" && (
            <span className="text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 border border-emerald-200 dark:border-transparent rounded-lg px-2 py-1 flex items-center gap-1">
              ✅ Configurada
            </span>
          )}
        </div>
        
        {activeProvider === "ollama" ? (
          <p className="text-sm text-gray-600 dark:text-gray-400 py-2">{t?.prefs.ollamaNoKey}</p>
        ) : (
          <div className="flex gap-2">
            <input
              type="password"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={`${selectedProviderConf?.keyPrefix || ""}...`}
              className="flex-1 rounded-xl border border-gray-300 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-600 outline-none focus:border-teal-500/50 dark:focus:border-teal-400/40 focus:ring-1 focus:ring-teal-500/20 transition-colors"
            />
            <button
              onClick={saveKey}
              disabled={(!inputValue.trim() && !isKeySavedForProvider) || saving}
              className="rounded-xl bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 hover:bg-teal-200 dark:hover:bg-teal-500/30 px-6 py-2 text-sm font-bold transition-all disabled:opacity-30 disabled:hover:bg-teal-100 dark:disabled:hover:bg-teal-500/20 flex items-center justify-center min-w-[100px]"
            >
              {saving ? "..." : t?.prefs.save}
            </button>
          </div>
        )}

        {/* Action for Ollama or Feedback */}
        {activeProvider === "ollama" && !saving && (
           <div className="mt-4 flex justify-end">
             <button
              onClick={saveKey}
              className="rounded-xl bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 hover:bg-teal-200 dark:hover:bg-teal-500/30 px-6 py-2 text-sm font-bold flex items-center justify-center transition-all"
             >
               Guardar y Usar Ollama
             </button>
           </div>
        )}

        {feedback && (
          <p className="mt-3 text-sm text-teal-600 dark:text-teal-400 animate-fade-in">{feedback}</p>
        )}
      </section>

    </div>
  );
}
