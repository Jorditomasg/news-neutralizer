"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { es, en, Translations } from "@/i18n/locales";

type Language = "es" | "en";

interface I18nContextProps {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
  // Extra user preferences that affect the backend prompts
  summaryLength: string;
  setSummaryLength: (val: string) => void;
  biasStrictness: string;
  setBiasStrictness: (val: string) => void;
}

const I18nContext = createContext<I18nContextProps | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("es");
  const [summaryLength, setSummaryLengthState] = useState("medium");
  const [biasStrictness, setBiasStrictnessState] = useState("standard");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const storedLang = localStorage.getItem("app_lang") as Language;
    if (storedLang === "en" || storedLang === "es") {
      setLanguageState(storedLang);
    }
    const storedLen = localStorage.getItem("app_summary_length");
    if (storedLen) setSummaryLengthState(storedLen);
    
    const storedBias = localStorage.getItem("app_bias_strictness");
    if (storedBias) setBiasStrictnessState(storedBias);
    
    setMounted(true);
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("app_lang", lang);
  };
  
  const setSummaryLength = (val: string) => {
    setSummaryLengthState(val);
    localStorage.setItem("app_summary_length", val);
  };
  
  const setBiasStrictness = (val: string) => {
    setBiasStrictnessState(val);
    localStorage.setItem("app_bias_strictness", val);
  };

  const t = language === "en" ? en : es;

  return (
    <I18nContext.Provider value={{
      language, setLanguage, t,
      summaryLength, setSummaryLength,
      biasStrictness, setBiasStrictness
    }}>
      <div className={!mounted ? "invisible flex-1 flex flex-col min-h-screen" : "flex-1 flex flex-col min-h-screen"}>
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
