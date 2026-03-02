"use client";

import type { ArticlePreview } from "@/types";
import type { Translations } from "@/i18n/es_ES";

interface HeadlineConfirmModalProps {
  readonly headline: ArticlePreview;
  readonly onConfirm: (headline: ArticlePreview) => void;
  readonly onCancel: () => void;
  readonly t: Translations;
}

export function HeadlineConfirmModal({ headline, onConfirm, onCancel, t }: HeadlineConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
        onKeyDown={(e) => { if (e.key === "Escape") onCancel(); }}
        role="button"
        tabIndex={0}
        aria-label="Close modal"
      />
      {/* Modal */}
      <div className="relative w-full max-w-xl rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111] shadow-2xl shadow-black/60 p-7 animate-fade-in transition-colors">
        {/* Header */}
        <div className="flex items-start gap-3 mb-5">
          <div className="shrink-0 mt-0.5 h-8 w-8 rounded-full bg-teal-500/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-widest text-teal-600 dark:text-teal-400 transition-colors mb-1">{t.search.selected_news_title}</p>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white transition-colors leading-snug">{headline.title}</h2>
          </div>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap gap-3 mb-6 text-sm text-gray-400">
          <div className="flex items-center gap-2 rounded-lg bg-white/5 dark:bg-white/5 border border-gray-200 dark:border-white/5 px-3 py-2">
            <span className="text-xs font-bold uppercase tracking-wide text-gray-500">{t.search.source}</span>
            <span className="font-semibold text-gray-900 dark:text-white">{headline.source_name}</span>
          </div>
          {headline.published_at && (
            <div className="flex items-center gap-2 rounded-lg bg-white/5 dark:bg-white/5 border border-gray-200 dark:border-white/5 px-3 py-2">
              <span className="text-xs font-bold uppercase tracking-wide text-gray-500">{t.search.date}</span>
              <span>{new Date(headline.published_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        {/* URL preview */}
        <div className="mb-7 rounded-lg bg-gray-50 dark:bg-white/[0.03] border border-gray-200 dark:border-white/5 transition-colors px-4 py-2.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">{t.search.link}</p>
          <a
            href={headline.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-teal-400/80 hover:text-teal-300 truncate block transition-colors"
          >
            {headline.source_url.length > 80
              ? headline.source_url.slice(0, 80) + "…"
              : headline.source_url}
          </a>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onConfirm(headline)}
            className="flex-1 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-gray-950 font-bold text-sm transition-all shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 active:scale-95"
          >
            {t.search.continue_analysis}
          </button>
          <button
            onClick={onCancel}
            className="flex-1 py-3 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/[0.03] hover:bg-gray-100 dark:hover:bg-white/[0.07] text-gray-700 dark:text-gray-300 font-semibold text-sm transition-all active:scale-95"
          >
            {t.search.cancel}
          </button>
        </div>
      </div>
    </div>
  );
}
