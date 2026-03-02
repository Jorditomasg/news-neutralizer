"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Article } from "@/types";
import { apiClient } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";

interface StructuredFactSummaryOut {
  id: number;
  article_id: number;
  content: string;
  type: string;
}

interface FactTraceabilityOut {
  id: number;
  structured_fact: StructuredFactSummaryOut;
}

interface GeneratedNewsDetailOut {
  id: number;
  title: string;
  lead: string;
  body: string;
  context_articles_ids: number[];
  reliability_score_achieved: number | null;
  has_new_context_available: boolean;
  created_at: string;
  traces: FactTraceabilityOut[];
  source_articles: Article[];
}

/** Renders paragraph text with highlighted [1], [2] citations */
function CitationText({ text }: Readonly<{ text: string }>) {
  const paragraphs = text.split("\n").filter((p) => p.trim() !== "");

  return (
    <>
      {paragraphs.map((paragraph, index) => {
        const parts = paragraph.split(/(\[\d+\])/g);
        return (
          <p
            key={`para-${index}`}
            className="mb-4 text-gray-700 dark:text-gray-300 leading-relaxed text-lg transition-colors"
          >
            {parts.map((part, i) =>
              part.match(/\[\d+\]/) ? (
                <span
                  key={`cite-${index}-${i}`}
                  className="inline-flex items-center justify-center bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-500/30 font-mono text-xs font-bold rounded px-1.5 mx-0.5 cursor-help transition-colors"
                  title="Referencia a hecho extraído"
                >
                  {part}
                </span>
              ) : (
                part
              )
            )}
          </p>
        );
      })}
    </>
  );
}

/** Bias score badge with color coding */
function BiasScoreBadge({ score, label }: Readonly<{ score: number; label: string }>) {
  const isHighBias = score > 0.6;
  const className = isHighBias
    ? "bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border-red-200 dark:border-red-500/20"
    : "bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-400 border-green-200 dark:border-green-500/20";

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border transition-colors ${className}`}>
      {label}
    </span>
  );
}

export default function GeneratedNewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const newsId = params.newsId as string;

  const [news, setNews] = useState<GeneratedNewsDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useI18n();

  useEffect(() => {
    if (!newsId) return;

    const fetchDetail = async () => {
      try {
        setLoading(true);
        const data = await apiClient(`/api/v1/generate/${newsId}`);
        setNews(data as GeneratedNewsDetailOut);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load generated news detail");
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [newsId]);

  if (loading) {
    return <LoadingSkeleton variant="detail" />;
  }

  if (error || !news) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6">
        <ErrorBanner
          error={error || t.generated.error_load}
          action={{ label: t.generated.back_button, onClick: () => router.push("/generated") }}
          centered
        />
      </div>
    );
  }

  const facts = news.traces.map((trace) => trace.structured_fact).filter((f) => f.type === "FACT");

  return (
    <div className="max-w-4xl mx-auto py-10 px-6 animate-fade-in">
      <Link href="/generated" className="inline-flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-8 group">
        <svg className="w-4 h-4 mr-2 transform group-hover:-translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        {t.generated.back_button}
      </Link>

      <article className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/5 rounded-3xl p-8 sm:p-12 shadow-sm dark:shadow-2xl relative overflow-hidden transition-colors">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500" />

        <header className="mb-10">
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <span className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-semibold bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20 transition-colors">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-500 dark:bg-purple-400 animate-pulse" />
              {t.generated.badge}
            </span>
            <span className="text-sm text-gray-500 font-medium transition-colors">
              {new Date(news.created_at).toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" })}
            </span>
          </div>

          <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 dark:text-white leading-tight mb-6 transition-colors">
            {news.title}
          </h1>

          <p className="text-xl sm:text-2xl text-gray-600 dark:text-gray-400 font-display leading-relaxed border-l-4 border-purple-500/50 pl-4 sm:pl-6 transition-colors">
            {news.lead}
          </p>
        </header>

        {/* Metrics Row */}
        <div className="flex flex-wrap gap-4 py-6 border-y border-gray-100 dark:border-white/5 mb-10 bg-gray-50/50 dark:bg-white/[0.01] -mx-8 px-8 sm:-mx-12 sm:px-12 transition-colors">
          {news.reliability_score_achieved !== null && (
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1 transition-colors">{t.generated.factual_consensus}</span>
              <span className="text-2xl font-display font-bold text-purple-600 dark:text-purple-400 transition-colors">
                {Math.round(news.reliability_score_achieved)}%
              </span>
            </div>
          )}
          <div className="w-px h-12 bg-gray-200 dark:bg-white/10 hidden sm:block mx-4 transition-colors" />
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1 transition-colors">{t.generated.analyzed_sources}</span>
            <span className="text-2xl font-display font-bold text-gray-900 dark:text-white transition-colors">
              {news.context_articles_ids.length}
            </span>
          </div>
          <div className="w-px h-12 bg-gray-200 dark:bg-white/10 hidden sm:block mx-4 transition-colors" />
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1 transition-colors">{t.generated.nuclear_facts}</span>
            <span className="text-2xl font-display font-bold text-gray-900 dark:text-white transition-colors">
              {facts.length}
            </span>
          </div>
        </div>

        {/* Main Body */}
        <div className="prose prose-gray dark:prose-invert prose-lg max-w-none prose-p:text-gray-700 dark:prose-p:text-gray-300 transition-colors">
          <CitationText text={news.body} />
        </div>
      </article>

      {/* Traceability Section */}
      <section className="mt-12 space-y-8">
        <div>
          <h3 className="text-2xl font-display font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3 transition-colors">
            <svg className="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            {t.generated.numeric_traceability}
          </h3>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/5 rounded-2xl p-6 shadow-sm dark:shadow-none transition-colors">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 transition-colors">{t.generated.traceability_desc}</p>
            <div className="grid gap-4">
              {facts.map((fact, idx) => (
                <div key={fact.id} className="flex gap-4 items-start p-4 bg-gray-50/50 dark:bg-white/[0.02] rounded-xl border border-gray-100 dark:border-white/5 transition-colors">
                  <span className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 font-mono text-sm font-bold transition-colors">
                    {idx + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-gray-800 dark:text-gray-200 text-sm leading-relaxed transition-colors">{fact.content}</p>
                    <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 transition-colors">
                      <span className="font-medium text-gray-700 dark:text-gray-400">{t.generated.internal_origin}</span> {t.generated.article_id.replace("{id}", fact.article_id.toString())}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sources Section */}
        <div>
          <h3 className="text-2xl font-display font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3 transition-colors">
            <svg className="w-6 h-6 text-teal-600 dark:text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            {t.generated.contrasted_sources}
          </h3>

          <div className="grid sm:grid-cols-2 gap-4">
            {news.source_articles.map((article) => (
              <a
                key={article.id}
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col p-5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/5 shadow-sm dark:shadow-none rounded-2xl hover:bg-gray-50 dark:hover:bg-white/[0.02] hover:border-teal-300 dark:hover:border-teal-500/30 transition-all"
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-500/20 transition-colors">
                    {article.source_name}
                  </span>
                  {article.bias_score !== null && (
                    <BiasScoreBadge
                      score={article.bias_score}
                      label={t.generated.bias.replace("{score}", Math.round(article.bias_score * 100).toString())}
                    />
                  )}
                </div>
                <h4 className="text-gray-900 dark:text-gray-200 font-bold group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors line-clamp-2 leading-snug mb-2">
                  {article.title}
                </h4>
                <div className="mt-auto pt-4 flex items-center justify-between text-xs text-gray-500 border-t border-gray-100 dark:border-white/5 transition-colors">
                  <span>{new Date(article.published_at || article.analyzed_at || "").toLocaleDateString()}</span>
                  <span className="flex items-center gap-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {t.generated.read_original}
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
