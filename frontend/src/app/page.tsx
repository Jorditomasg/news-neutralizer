"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/context/I18nContext";

export default function HomePage() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const router = useRouter();

  const isUrl = /^https?:\/\//.exec(query.trim()) !== null;

  const handleSearch = (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <div className="flex flex-col items-center pt-20 pb-16">
      {/* Hero */}
      <div className="mb-12 text-center">
        <h1 className="font-display text-5xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-6xl transition-colors">
          {t.home.hero_title}
          <span className="bg-gradient-to-r from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-400 bg-clip-text text-transparent">
            {t.home.hero_highlight}
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-gray-600 dark:text-gray-400 transition-colors">
          {t.home.hero_desc}
        </p>
      </div>

      {/* Unified Search Form */}
      <form
        onSubmit={handleSearch}
        className="w-full max-w-2xl"
      >
        <div className="group relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.home.placeholder}
            className="w-full rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 py-4 pl-6 pr-36 text-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm dark:shadow-none outline-none transition-all focus:border-teal-400/50 dark:focus:border-teal-400/40 focus:bg-white hover:bg-gray-50 dark:hover:bg-white/[0.07] dark:focus:bg-white/[0.07] focus:ring-2 focus:ring-teal-500/10 dark:focus:ring-teal-400/20"
          />
          
          {/* Input Type Indicator Badge */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            
            <button
              type="submit"
              disabled={!query.trim()}
              className="rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-400 px-5 py-2 text-sm font-semibold text-white dark:text-gray-950 transition-all hover:shadow-lg hover:shadow-teal-500/25 disabled:opacity-40"
            >
              {isUrl ? t?.home.analyze_url : t?.home.search}
            </button>
          </div>
        </div>
      </form>
      
      <div className="mt-8">
      </div>

      {/* Feature Cards */}
      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        <div className="rounded-2xl border border-gray-100 dark:border-white/5 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="mb-3 text-2xl">📊</div>
          <h3 className="font-display text-sm font-semibold text-gray-900 dark:text-white transition-colors">
            {t.home.feature1_title}
          </h3>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-500 transition-colors">
            {t.home.feature1_desc}
          </p>
        </div>
        <div className="rounded-2xl border border-gray-100 dark:border-white/5 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="mb-3 text-2xl">🎯</div>
          <h3 className="font-display text-sm font-semibold text-gray-900 dark:text-white transition-colors">
            {t.home.feature2_title}
          </h3>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-500 transition-colors">
            {t.home.feature2_desc}
          </p>
        </div>
        <div className="rounded-2xl border border-gray-100 dark:border-white/5 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="mb-3 text-2xl">✍️</div>
          <h3 className="font-display text-sm font-semibold text-gray-900 dark:text-white transition-colors">
            {t.home.feature3_title}
          </h3>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-500 transition-colors">
            {t.home.feature3_desc}
          </p>
        </div>
      </div>
    </div>
  );
}
