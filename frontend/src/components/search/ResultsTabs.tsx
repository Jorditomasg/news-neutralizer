"use client";

import type { SearchTask, SourceBiasScore } from "@/types";
import type { Translations } from "@/i18n/es_ES";
import { FeedbackButtons } from "@/components/feedback/FeedbackButtons";
import { useRouter } from "next/navigation";

interface ResultsTabsProps {
  readonly task: SearchTask;
  readonly activeTab: "article" | "bias" | "sources";
  readonly onTabChange: (tab: "article" | "bias" | "sources") => void;
  readonly t: Translations;
}

// ── Helper functions ──────────────────────────────────────────

function getBiasColor(score: number) {
  if (score < 0.3) return { bg: "bg-emerald-500/10", text: "text-emerald-400", bar: "bg-emerald-500" };
  if (score < 0.6) return { bg: "bg-amber-500/10", text: "text-amber-400", bar: "bg-amber-500" };
  return { bg: "bg-red-500/10", text: "text-red-400", bar: "bg-red-500" };
}

function getSeverityLabel(severity: number) {
  const labels = ["", "Muy sutil", "Sutil", "Moderado", "Notable", "Grave"];
  return labels[severity] || "Moderado";
}

function getDirectionIcon(direction: string) {
  switch (direction) {
    case "izquierda": return "←";
    case "derecha": return "→";
    case "centro": return "◆";
    case "sensacionalista": return "⚡";
    default: return "•";
  }
}

function getBiasTypeStyle(type: string): string {
  switch (type) {
    case "sensacionalismo": return "bg-red-100/50 dark:bg-red-500/10 text-red-600 dark:text-red-400";
    case "omisión": return "bg-purple-100/50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400";
    case "framing": return "bg-amber-100/50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400";
    case "adjetivación": return "bg-orange-100/50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400";
    default: return "bg-pink-100/50 dark:bg-pink-500/10 text-pink-600 dark:text-pink-400";
  }
}

function getSeverityDotColor(severity: number): string {
  if (severity >= 4) return "bg-red-400";
  if (severity >= 3) return "bg-amber-400";
  return "bg-yellow-400/60";
}

function getArticleStatusStyle(status: string): string {
  if (status === "ANALYZING") {
    return "bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 ring-amber-400/50 dark:ring-amber-500/30";
  }
  return "bg-gray-200 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300 ring-gray-400 dark:ring-gray-500/30";
}

function getArticleStatusLabel(status: string, t: Translations): string {
  if (status === "DETECTED") return t.search.detected;
  if (status === "ANALYZING") return t.search.analyzing;
  return status || t.search.detected;
}

// ── Tab Components ────────────────────────────────────────────

function NeutralizedArticleTab({ task }: Readonly<{ task: SearchTask }>) {
  const analysis = task.analysis;
  if (!analysis) return null;

  const articleObj = analysis.neutralized_article;
  const paragraphs = articleObj?.content ? articleObj.content.split("\n").filter((p) => p.trim()) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="rounded-2xl border border-teal-500/20 bg-gradient-to-br from-teal-500/5 to-cyan-500/5 p-6">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-5 w-5 rounded-full bg-teal-100 dark:bg-teal-400/20 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-teal-600 dark:bg-teal-400" />
          </div>
          <span className="text-xs font-medium text-teal-700 dark:text-teal-400 tracking-wider uppercase">Resumen del tema</span>
        </div>
        <p className="text-gray-800 dark:text-gray-200 leading-relaxed text-lg transition-colors">
          {analysis.topic_summary}
        </p>
      </div>

      <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none overflow-hidden transition-colors">
        <div className="border-b border-gray-100 dark:border-white/10 px-6 py-4 bg-gray-50/50 dark:bg-white/[0.02] transition-colors">
          <div className="flex items-center gap-2">
            <span className="text-lg">✍️</span>
            <h2 className="font-display text-lg font-bold text-gray-900 dark:text-white transition-colors">
              Artículo neutralizado
            </h2>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Generado por IA a partir de {task.articles.length} fuentes · {analysis.provider_used}
          </p>
        </div>
        <div className="p-6 md:p-8">
          {articleObj && (
            <article className="prose-custom prose-gray dark:prose-invert">
              {articleObj.title && (
                <h2 className="font-display text-2xl md:text-3xl font-bold text-gray-900 dark:text-white mb-6 leading-tight transition-colors">
                  {articleObj.title.replace(/^\[?TITULAR[:\s]*/i, "").replace(/\]$/, "").trim()}
                </h2>
              )}
              {paragraphs.map((paragraph, i) => (
                <p key={`art-p-${i}`} className={`text-gray-700 dark:text-gray-300 leading-relaxed transition-colors ${i === 0 ? "text-lg font-medium border-l-2 border-teal-500/40 pl-4 mb-6" : "mb-4"}`}>
                  {paragraph.replace(/^\[?CUERPO[:\s]*/i, "").replace(/^\[?ENTRADILLA[:\s]*/i, "").replace(/^\[?CONCLUSI[ÓO]N[:\s]*/i, "").replace(/\]$/, "")}
                </p>
              ))}
            </article>
          )}
        </div>
        <div className="border-t border-white/10 px-6 py-4 bg-white/[0.01] flex justify-end">
          <FeedbackButtons targetType="analysis" targetId={task.task_id} />
        </div>
      </div>

      {analysis.objective_facts.length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">📋</span>
            <h2 className="font-display text-lg font-bold text-gray-900 dark:text-white transition-colors">Hechos verificados</h2>
            <span className="ml-auto rounded-full bg-teal-100 dark:bg-teal-500/10 px-2.5 py-0.5 text-xs font-medium text-teal-700 dark:text-teal-400">
              {analysis.objective_facts.length}
            </span>
          </div>
          <div className="grid gap-2">
            {analysis.objective_facts.map((fact, i) => (
              <div key={`fact-${i}`} className="flex gap-3 items-start rounded-xl bg-gray-50 dark:bg-white/[0.02] p-3 border border-gray-100 dark:border-white/5 transition-colors">
                <span className="shrink-0 mt-0.5 h-5 w-5 rounded-full bg-teal-100 dark:bg-teal-500/10 flex items-center justify-center text-xs font-bold text-teal-600 dark:text-teal-400">
                  {i + 1}
                </span>
                <span className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed transition-colors">{fact}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BiasTab({ task }: Readonly<{ task: SearchTask }>) {
  const analysis = task.analysis;
  if (!analysis) return null;

  return (
    <div className="space-y-4 animate-fade-in">
      {analysis.bias_elements.length > 0 ? (
        <>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors">
              Se detectaron <span className="text-gray-900 dark:text-white font-medium transition-colors">{analysis.bias_elements.length}</span> elementos de sesgo
            </p>
          </div>
          {analysis.bias_elements.map((bias, i) => (
            <div
              key={`${bias.source}-${bias.type}-${i}`}
              className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none overflow-hidden transition-all hover:border-gray-300 dark:hover:border-white/20"
            >
              <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-white/5 bg-gray-50/50 dark:bg-white/[0.01]">
                <span className={`rounded-lg px-2.5 py-1 text-xs font-bold tracking-wide uppercase ${getBiasTypeStyle(bias.type)}`}>
                  {bias.type}
                </span>
                <span className="text-xs text-gray-500">en</span>
                <span className="text-sm font-medium text-gray-800 dark:text-gray-300">{bias.source}</span>
                <div className="flex gap-1 ml-auto items-center">
                  <span className="text-xs text-gray-500 mr-1">{getSeverityLabel(bias.severity)}</span>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <div
                      key={`sev-${j}`}
                      className={`h-2.5 w-2.5 rounded-sm transition-all ${
                        j < bias.severity ? getSeverityDotColor(bias.severity) : "bg-white/10"
                      }`}
                    />
                  ))}
                </div>
              </div>
              <div className="px-5 py-4 space-y-3">
                <blockquote className="text-sm text-gray-500 dark:text-gray-400 italic border-l-2 border-amber-500/30 pl-4 py-1 transition-colors">
                  &quot;{bias.original_text}&quot;
                </blockquote>
                <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed transition-colors">
                  <span className="text-teal-600 dark:text-teal-400 font-medium transition-colors">Análisis: </span>
                  {bias.explanation}
                </p>
              </div>
            </div>
          ))}
        </>
      ) : (
        <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] p-8 text-center shadow-sm dark:shadow-none transition-colors">
          <span className="text-4xl mb-3 block">✅</span>
          <p className="text-gray-700 dark:text-gray-300 transition-colors">No se detectaron elementos de sesgo significativos</p>
        </div>
      )}
    </div>
  );
}

function SourcesTab({ task, t }: Readonly<{ task: SearchTask; t: Translations }>) {
  const analysis = task.analysis;
  const router = useRouter();

  return (
    <div className="space-y-6 animate-fade-in">
      {analysis && Object.keys(analysis.source_bias_scores).length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="flex items-center gap-2 mb-5">
            <span className="text-lg">📊</span>
            <h2 className="font-display text-lg font-bold text-gray-900 dark:text-white transition-colors">Comparación de sesgo por fuente</h2>
          </div>
          <div className="space-y-4">
            {(Object.entries(analysis.source_bias_scores) as [string, SourceBiasScore][])
              .sort(([, a], [, b]) => b.score - a.score)
              .map(([source, typedScores]) => {
                const color = getBiasColor(typedScores.score);
                return (
                  <div key={source} className="rounded-xl border border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-white/[0.02] p-4 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{getDirectionIcon(typedScores.direction)}</span>
                        <span className="font-medium text-gray-900 dark:text-white transition-colors">{source}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <FeedbackButtons targetType="domain" targetId={source} compact />
                        <div className="flex items-center gap-2">
                          <span className={`rounded-lg px-2 py-0.5 text-xs font-medium capitalize ${color.bg} ${color.text}`}>
                            {typedScores.direction}
                          </span>
                          <span className={`font-mono text-sm font-bold ${color.text}`}>
                            {(typedScores.score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full ${color.bar} transition-all duration-700`}
                        style={{ width: `${typedScores.score * 100}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1.5 transition-colors">
                      <span className="text-[10px] text-gray-500 dark:text-gray-400">{t.search.neutral}</span>
                      <span className="text-[10px] text-gray-500 dark:text-gray-400">{t.search.confidence}{((typedScores.confidence || 0) * 100).toFixed(0)}%</span>
                      <span className="text-[10px] text-gray-500 dark:text-gray-400">{t.search.max_bias}</span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {task.articles.length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.02] shadow-sm dark:shadow-none p-6 transition-colors">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">📰</span>
            <h2 className="font-display text-lg font-bold text-gray-900 dark:text-white transition-colors">{t.search.related_articles}</h2>
            <span className="ml-auto rounded-full bg-gray-100 dark:bg-white/5 px-2.5 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-400">
              {task.articles.length}
            </span>
          </div>
          <div className="space-y-2">
            {task.articles.map((article) => {
              const isAnalyzed = article.status === "ANALYZED" || article.status === "CONTEXTUALIZED";
              return (
                <div
                  key={article.id}
                  className="flex items-center gap-4 rounded-xl border border-gray-100 dark:border-white/5 bg-gray-50/50 dark:bg-white/[0.02] p-4 transition-all hover:border-teal-300 dark:hover:border-teal-500/20 hover:bg-white dark:hover:bg-white/[0.04] group"
                >
                  <div className="min-w-0 flex-1">
                    <a
                      href={article.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-gray-900 dark:text-white truncate block group-hover:text-teal-600 dark:group-hover:text-teal-300 transition-colors"
                    >
                      {article.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-medium text-gray-400">{article.source_name}</span>
                      {article.author && (
                        <>
                          <span className="text-gray-600">·</span>
                          <span className="text-xs text-gray-500 truncate max-w-[200px]">{article.author}</span>
                        </>
                      )}
                      {article.published_at && (
                        <>
                          <span className="text-gray-600">·</span>
                          <span className="text-xs text-gray-500">
                            {new Date(article.published_at).toLocaleDateString("es-ES")}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {article.is_source && (
                    <span className="shrink-0 rounded-md bg-blue-100 dark:bg-blue-500/20 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300 ring-1 ring-inset ring-blue-500/30">
                      {t.search.base_article}
                    </span>
                  )}

                  {isAnalyzed ? (
                    <span className="shrink-0 rounded-md bg-teal-100 dark:bg-teal-500/20 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300 ring-1 ring-inset ring-teal-500/30 flex items-center gap-1">
                      ✅ {t.search.analyzed}
                    </span>
                  ) : (
                    <span className={`shrink-0 rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider ring-1 ring-inset ${getArticleStatusStyle(article.status)}`}>
                      {getArticleStatusLabel(article.status, t)}
                    </span>
                  )}

                  {article.bias_score !== null && article.bias_score !== undefined && (
                    <div className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-mono font-bold ${getBiasColor(article.bias_score).bg} ${getBiasColor(article.bias_score).text}`}>
                      {(article.bias_score * 100).toFixed(0)}%
                    </div>
                  )}

                  {!article.is_source && !isAnalyzed && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/search?q=${encodeURIComponent(article.source_url)}`);
                      }}
                      className="shrink-0 rounded-lg bg-gradient-to-r from-teal-500/80 to-cyan-500/80 px-3 py-1.5 text-[11px] font-bold text-gray-950 transition-all hover:from-teal-400 hover:to-cyan-400 hover:shadow-md hover:shadow-teal-500/20 active:scale-95"
                    >
                      {t.search.analyze_button}
                    </button>
                  )}

                  <FeedbackButtons targetType="article" targetId={article.id} compact />
                  <a
                    href={article.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0"
                  >
                    <svg className="w-4 h-4 text-gray-500 group-hover:text-teal-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────

const TABS = [
  { key: "article" as const, label: "📝 Artículo neutralizado" },
  { key: "bias" as const, label: "🎯 Sesgo detectado" },
  { key: "sources" as const, label: "📊 Posibles Fuentes" },
];

export function ResultsTabs({ task, activeTab, onTabChange, t }: ResultsTabsProps) {
  return (
    <div className="space-y-6">
      <div className="flex gap-1 p-1 rounded-xl bg-gray-100 dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 transition-colors">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? "bg-teal-50 dark:bg-white/10 text-teal-800 dark:text-gray-100 shadow-sm dark:shadow-none border border-teal-200 dark:border-white/10"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/[0.03]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "article" && <NeutralizedArticleTab task={task} />}
      {activeTab === "bias" && <BiasTab task={task} />}
      {activeTab === "sources" && <SourcesTab task={task} t={t} />}

      {!task.analysis && task.articles.length > 0 && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-6">
          <div className="flex gap-3 items-start">
            <span className="text-2xl">⏳</span>
            <div>
              <h3 className="font-bold text-amber-800 dark:text-amber-400 mb-1">{t.search.articles_no_analysis}</h3>
              <p className="text-amber-700/80 dark:text-amber-300/70 text-sm">
                {t.search.articles_no_analysis_desc.replace("{count}", task.articles.length.toString())}
                <br />
                {t.search.verify_ollama}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
