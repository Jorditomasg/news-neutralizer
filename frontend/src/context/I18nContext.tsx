"use client";

import React, { createContext, useContext, useState, useMemo } from "react";
import { locales, DEFAULT_LOCALE, type LocaleKey } from "@/i18n/index";
import type { Translations } from "@/i18n/es_ES";
import { useIsClient } from "@/hooks/useIsClient";

/** Shape of each entry in the available languages list. */
export interface LanguageOption {
  key: LocaleKey;
  label: string;
  flag: string;
  iso: string;
}

interface I18nContextProps {
  locale: LocaleKey;
  setLocale: (locale: LocaleKey) => void;
  t: Translations;
  availableLanguages: LanguageOption[];
  summaryLength: string;
  setSummaryLength: (val: string) => void;
  biasStrictness: string;
  setBiasStrictness: (val: string) => void;
}

const I18nContext = createContext<I18nContextProps | undefined>(undefined);

/** Build the available languages list once from the registry. */
const availableLanguages: LanguageOption[] = Object.entries(locales).map(
  ([key, locale]) => ({
    key: key as LocaleKey,
    label: locale.label,
    flag: locale.flag,
    iso: locale.iso,
  })
);

function getInitialLocale(): LocaleKey {
  if (globalThis.window === undefined) return DEFAULT_LOCALE;
  const storedLocale = localStorage.getItem("app_locale") as LocaleKey | null;
  if (storedLocale && storedLocale in locales) return storedLocale;
  // Backwards-compat: migrate old 'app_lang' values (es/en) to locale keys
  const oldLang = localStorage.getItem("app_lang");
  if (oldLang === "en") return "en_GB";
  if (oldLang === "es") return "es_ES";
  return DEFAULT_LOCALE;
}

export function I18nProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [locale, setLocaleRaw] = useState<LocaleKey>(getInitialLocale);
  const [summaryLength, setSummaryLengthRaw] = useState(() => {
    if (globalThis.window === undefined) return "medium";
    return localStorage.getItem("app_summary_length") || "medium";
  });
  const [biasStrictness, setBiasStrictnessRaw] = useState(() => {
    if (globalThis.window === undefined) return "standard";
    return localStorage.getItem("app_bias_strictness") || "standard";
  });
  const isClient = useIsClient();

  const setLocale = (key: LocaleKey) => {
    setLocaleRaw(key);
    localStorage.setItem("app_locale", key);
  };

  const setSummaryLength = (val: string) => {
    setSummaryLengthRaw(val);
    localStorage.setItem("app_summary_length", val);
  };

  const setBiasStrictness = (val: string) => {
    setBiasStrictnessRaw(val);
    localStorage.setItem("app_bias_strictness", val);
  };

  const t = locales[locale].translations;

  const value = useMemo<I18nContextProps>(
    () => ({
      locale,
      setLocale,
      t,
      availableLanguages,
      summaryLength,
      setSummaryLength,
      biasStrictness,
      setBiasStrictness,
    }),
    [locale, t, summaryLength, biasStrictness]
  );

  return (
    <I18nContext.Provider value={value}>
      <div
        className={
          isClient
            ? "flex-1 flex flex-col min-h-screen"
            : "invisible flex-1 flex flex-col min-h-screen"
        }
      >
        {children}
      </div>
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
