"use client";

import type { ArticlePreview } from "@/types";
import type { Translations } from "@/i18n/es_ES";

interface ArticlePreviewCardProps {
  readonly previewData: ArticlePreview;
  readonly onStartAnalysis: () => void;
  readonly t: Translations;
}

export function ArticlePreviewCard({ previewData, onStartAnalysis, t }: ArticlePreviewCardProps) {
  return (
    <div className="mb-10 animate-fade-in relative z-10">
      <div className="rounded-3xl border border-gray-200/50 dark:border-white/10 bg-white dark:bg-[#111] shadow-2xl shadow-teal-500/5 overflow-hidden transition-colors flex flex-col md:flex-row">
        {/* Left side: Image or Pattern */}
        <div className="md:w-5/12 relative min-h-[250px] md:min-h-full bg-gray-100 dark:bg-zinc-900 overflow-hidden shrink-0">
          {previewData.image_url ? (
            <>
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent z-10" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewData.image_url}
                alt={previewData.title}
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 hover:scale-105"
              />
              {/* Floating Action Button over image on desktop */}
              <div className="absolute bottom-6 left-6 right-6 z-20 hidden md:block">
                <button
                  onClick={onStartAnalysis}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-gray-950 font-bold text-sm transition-all shadow-lg shadow-teal-500/25 hover:shadow-cyan-500/30 active:scale-95 flex justify-center items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                  <span>{t.search.deep_analysis}</span>
                </button>
              </div>
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center opacity-10 scale-150">
              <span className="text-9xl">📰</span>
            </div>
          )}
        </div>

        {/* Right side: Content */}
        <div className="p-8 md:p-10 flex flex-col flex-1 relative">
          <div className="flex items-center gap-3 mb-4">
            <span className="bg-teal-500/10 text-teal-600 dark:text-teal-400 px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase">
              {previewData.source_name}
            </span>
            {previewData.published_at && (
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
                {new Date(previewData.published_at).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })}
              </span>
            )}
            {previewData.has_paywall && (
              <span className="bg-amber-500/10 text-amber-600 dark:text-amber-400 px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase ml-auto">
                {t.search.possible_paywall}
              </span>
            )}
          </div>

          <h2 className="text-2xl md:text-3xl font-display font-bold text-gray-900 dark:text-white mb-6 leading-tight transition-colors">
            {previewData.title}
          </h2>

          <div className="prose-custom prose-gray dark:prose-invert max-w-none flex-1 mb-8">
            {previewData.body ? (
              <>
                <p className="text-gray-700 dark:text-gray-300 text-lg font-medium leading-relaxed border-l-2 border-teal-500/40 pl-4 mb-5">
                  {previewData.body.split("\n").find((p) => p.trim() && p.trim().length > 20) || t.search.no_summary}
                </p>
                <div className="space-y-4 text-gray-600 dark:text-gray-400 leading-relaxed text-[15px] relative">
                  <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white dark:from-[#111] to-transparent z-10 pointer-events-none" />
                  {previewData.body
                    .split("\n")
                    .filter((p) => p.trim())
                    .slice(1, 4)
                    .map((p, i) => (
                      <p key={`preview-p-${i}`}>{p}</p>
                    ))}
                </div>
              </>
            ) : (
              <p className="text-gray-500 italic">No se pudo extraer el contenido del artículo. Procede al análisis para más detalles.</p>
            )}
          </div>

          <div className="mt-auto block md:hidden">
            <button
              onClick={onStartAnalysis}
              className="w-full py-4 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-gray-950 font-bold text-sm transition-all shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 active:scale-95 flex justify-center items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
              <span>{t.search.send_to_ai}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
