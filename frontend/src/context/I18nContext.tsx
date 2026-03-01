"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { locales, DEFAULT_LOCALE, type LocaleKey } from "@/i18n/index";
import type { Translations } from "@/i18n/es_ES";

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
  // Extra user preferences that affect the backend prompts
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

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleKey>(DEFAULT_LOCALE);
  const [summaryLength, setSummaryLengthState] = useState("medium");
  const [biasStrictness, setBiasStrictnessState] = useState("standard");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const storedLocale = localStorage.getItem("app_locale") as LocaleKey | null;
    if (storedLocale && storedLocale in locales) {
      setLocaleState(storedLocale);
    } else {
      // Backwards-compat: migrate old 'app_lang' values (es/en) to locale keys
      const oldLang = localStorage.getItem("app_lang");
      if (oldLang === "en") setLocaleState("en_GB");
      else if (oldLang === "es") setLocaleState("es_ES");
    }

    const storedLen = localStorage.getItem("app_summary_length");
    if (storedLen) setSummaryLengthState(storedLen);

    const storedBias = localStorage.getItem("app_bias_strictness");
    if (storedBias) setBiasStrictnessState(storedBias);

    setMounted(true);
  }, []);

  const setLocale = (key: LocaleKey) => {
    setLocaleState(key);
    localStorage.setItem("app_locale", key);
  };

  const setSummaryLength = (val: string) => {
    setSummaryLengthState(val);
    localStorage.setItem("app_summary_length", val);
  };

  const setBiasStrictness = (val: string) => {
    setBiasStrictnessState(val);
    localStorage.setItem("app_bias_strictness", val);
  };

  const t = locales[locale].translations as Translations;

  return (
    <I18nContext.Provider
      value={{
        locale,
        setLocale,
        t,
        availableLanguages,
        summaryLength,
        setSummaryLength,
        biasStrictness,
        setBiasStrictness,
      }}
    >
      <div
        className={
          !mounted
            ? "invisible flex-1 flex flex-col min-h-screen"
            : "flex-1 flex flex-col min-h-screen"
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
