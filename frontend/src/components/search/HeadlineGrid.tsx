"use client";

import type { ArticlePreview } from "@/types";
import type { Translations } from "@/i18n/es_ES";

interface HeadlineGridProps {
  readonly headlines: ArticlePreview[];
  readonly query: string;
  readonly isAmbiguous: boolean;
  readonly failedUrls: Set<string>;
  readonly onSelect: (headline: ArticlePreview) => void;
  readonly onAnalyzeGlobal: () => void;
  readonly t: Translations;
}

export function HeadlineGrid({
  headlines,
  query,
  isAmbiguous,
  failedUrls,
  onSelect,
  onAnalyzeGlobal,
  t,
}: HeadlineGridProps) {
  return (
    <div className="animate-fade-in space-y-6 mb-12">
      <div className="rounded-2xl border border-teal-500/20 bg-teal-50 dark:bg-teal-500/5 p-6 backdrop-blur-sm transition-colors">
        <div className="flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white transition-colors mb-2">
              {headlines.length > 0 ? t.search.what_to_analyze : t.search.no_headlines}
            </h2>
            <p className="text-gray-600 dark:text-gray-400 transition-colors text-sm">
              {headlines.length > 0 ? (
                <>Hemos encontrado varias noticias recientes sobre <span className="text-teal-600 dark:text-teal-400 transition-colors">&quot;{query}&quot;</span>.<br />Selecciona una noticia específica o analiza el tema en general.</>
              ) : (
                <>No pudimos encontrar noticias recientes de forma rápida sobre <span className="text-teal-600 dark:text-teal-400 transition-colors">&quot;{query}&quot;</span>.<br />Puedes forzar un análisis profundo para que la IA busque exhaustivamente en la red.</>
              )}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            {!isAmbiguous ? (
              <button
                onClick={onAnalyzeGlobal}
                className="whitespace-nowrap px-6 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-600 hover:from-teal-400 hover:to-cyan-500 text-white font-bold shadow-lg shadow-teal-500/20 transition-all transform hover:scale-105 active:scale-95 ring-1 ring-white/20"
              >
                ⚡ {t.search.analyze_global}
              </button>
            ) : (
              <div className="text-right">
                <span className="text-amber-400 text-xs font-bold uppercase tracking-wider bg-amber-500/10 px-2 py-1 rounded">
                  Tema demasiado amplio
                </span>
                <p className="text-gray-400 text-xs mt-1 max-w-[200px]">
                  Selecciona una noticia concreta para continuar.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {headlines.map((headline) => {
          const isFailed = failedUrls.has(headline.source_url);
          return (
            <button
              key={headline.source_url}
              onClick={() => onSelect(headline)}
              className={`text-left group relative flex flex-col justify-between h-full rounded-xl border p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-teal-900/10 ${
                isFailed
                  ? "border-amber-500/30 bg-amber-50/50 hover:bg-amber-50 dark:bg-amber-500/[0.04] dark:hover:bg-amber-500/[0.07]"
                  : "border-gray-200 dark:border-white/5 bg-white dark:bg-white/[0.02] hover:bg-gray-50 dark:hover:bg-white/[0.05] hover:border-teal-300 dark:hover:border-teal-500/30 shadow-sm dark:shadow-none"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold tracking-wider text-teal-400 uppercase bg-teal-500/10 px-2 py-0.5 rounded-md">
                      {headline.source_name || "Noticia"}
                    </span>
                    {isFailed && (
                      <span className="text-[10px] font-bold tracking-wider text-amber-400 uppercase bg-amber-500/10 px-2 py-0.5 rounded-md flex items-center gap-1">
                        ⚠️ Error previo
                      </span>
                    )}
                  </div>
                  {headline.published_at && (
                    <span className="text-[10px] text-gray-500">
                      {new Date(headline.published_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <h3 className="font-bold text-gray-900 dark:text-gray-200 group-hover:text-teal-600 dark:group-hover:text-white mb-3 line-clamp-3 leading-snug transition-colors">
                  {headline.title}
                </h3>
              </div>
              <div className="mt-4 flex items-center text-xs font-medium text-gray-500 group-hover:text-teal-400 transition-colors">
                <span>{isFailed ? "Reintentar análisis" : "Analizar esta noticia"}</span>
                <svg className="w-3 h-3 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
