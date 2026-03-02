"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { SearchTask, ArticlePreview } from "@/types";
import { SearchProgress } from "@/components/search/SearchProgress";
import { useSmoothProgress } from "@/hooks/useSmoothProgress";
import { useTaskContext } from "@/context/TaskContext";
import { apiClient, ApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { HeadlineConfirmModal } from "@/components/search/HeadlineConfirmModal";
import { ArticlePreviewCard } from "@/components/search/ArticlePreviewCard";
import { HeadlineGrid } from "@/components/search/HeadlineGrid";
import { WarningBanner } from "@/components/search/WarningBanner";
import { ResultsTabs } from "@/components/search/ResultsTabs";


const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function SearchContent() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const initialTaskId = searchParams.get("taskId");
  const { addTask } = useTaskContext();
  const router = useRouter();
  const [taskId, setTaskId] = useState<string | null>(initialTaskId);
  const [status, setStatus] = useState<string>(initialTaskId ? "pending" : "idle");
  const [progress, setProgress] = useState(0);
  const [expectedDurationMs, setExpectedDurationMs] = useState(0);
  const { displayProgress } = useSmoothProgress(taskId, progress, status, expectedDurationMs);
  const [message, setMessage] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [task, setTask] = useState<SearchTask | null>(null);
  const [previewData, setPreviewData] = useState<ArticlePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const hasStarted = useRef(false);
  const [activeTab, setActiveTab] = useState<"article" | "bias" | "sources">("article");
  const [headlines, setHeadlines] = useState<ArticlePreview[]>([]);
  const [showHeadlines, setShowHeadlines] = useState(false);
  const [selectedHeadline, setSelectedHeadline] = useState<ArticlePreview | null>(null);
  const [isAmbiguous, setIsAmbiguous] = useState(false);
  const [failedHeadlineUrls, setFailedHeadlineUrls] = useState<Set<string>>(new Set());
  const [pendingHeadline, setPendingHeadline] = useState<ArticlePreview | null>(null);

  const isUrl = (text: string) => text.startsWith("http://") || text.startsWith("https://");

  // ── Data Fetching ────────────────────────────────────────────

  const fetchHeadlines = async (searchQuery: string) => {
    try {
      setStatus("headlines_loading");
      const data = await apiClient("/api/v1/search/headlines", {
        method: "POST",
        body: JSON.stringify({ query: searchQuery }),
      });
      setHeadlines((data as ArticlePreview[]) || []);
      setShowHeadlines(true);
      setStatus("headlines_selection");
    } catch (e) {
      console.warn("Headlines fetch failed", e);
      setHeadlines([]);
      setShowHeadlines(true);
      setStatus("headlines_selection");
    }
  };

  const recoverToHeadlines = (failedUrl?: string, errorMsg?: string) => {
    if (headlines.length > 0) {
      if (failedUrl) {
        setFailedHeadlineUrls((prev) => new Set(prev).add(failedUrl));
      }
      setError(errorMsg || null);
      setStatus("headlines_selection");
      setShowHeadlines(true);
      setTaskId(null);
      setTask(null);
      setProgress(0);
      setMessage("");
      setWarnings([]);
      setSelectedHeadline(null);
    } else {
      setError(errorMsg || "Error durante el procesamiento");
      setStatus("error");
    }
  };

  const submitSearchTask = async (searchQuery: string, payload: Record<string, string>, headline?: ArticlePreview) => {
    const data = await apiClient("/api/v1/search/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const resData = data as { task_id: string; expected_duration_ms?: number };
    setTaskId(resData.task_id);
    if (resData.expected_duration_ms) setExpectedDurationMs(resData.expected_duration_ms);
    addTask(resData.task_id, headline ? headline.title : searchQuery || "Analizando noticia...");
    setStatus("pending");
  };

  const startSearch = async (searchQuery: string, headline?: ArticlePreview) => {
    try {
      setStatus("starting");
      setError(null);
      setPreviewData(null);
      setShowHeadlines(false);
      setWarnings([]);
      setSelectedHeadline(headline || null);

      const payload: Record<string, string> = { query: searchQuery };
      if (headline && !isUrl(query)) {
        payload.original_query = query;
      }

      await submitSearchTask(searchQuery, payload, headline);
    } catch (e: unknown) {
      handleSearchError(e, headline);
    }
  };

  const handleSearchError = (e: unknown, headline?: ArticlePreview) => {
    if (e instanceof ApiError && e.status === 400 && e.body.includes("AMBIGUOUS_TOPIC")) {
      try {
        const errorData = JSON.parse(e.body);
        if (errorData.detail?.includes?.("AMBIGUOUS_TOPIC")) {
          const reason = errorData.detail.replace("AMBIGUOUS_TOPIC: ", "");
          setIsAmbiguous(true);
          setError(`Tema demasiado amplio: ${reason}. Por favor, selecciona una noticia concreta de la lista.`);
          setStatus("headlines_selection");
          setShowHeadlines(true);
          return;
        }
      } catch { /* parse error — fall through */ }
    }

    if (!isAmbiguous) {
      const errorMsg = getSearchErrorMessage(e);
      recoverToHeadlines(headline?.source_url, errorMsg);
    }
    hasStarted.current = false;
  };

  const getSearchErrorMessage = (e: unknown): string => {
    if (e instanceof ApiError) return e.message;
    if (e instanceof Error) return e.message;
    return "No se pudo iniciar la búsqueda. ¿Está el backend corriendo?";
  };

  const fetchPreview = async (url: string) => {
    try {
      setStatus("preview");
      const data = await apiClient("/api/v1/search/preview", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      setPreviewData(data as ArticlePreview);
    } catch (e) {
      console.error("Preview failed, falling back to direct search", e);
      startSearch(url);
    }
  };

  const fetchResults = async (id: string) => {
    try {
      const data = await apiClient(`/api/v1/search/${id}`);
      const resData = data as SearchTask;
      setTask(resData);
      setStatus(resData.status);
      if (resData.warnings?.length) {
        setWarnings(resData.warnings);
      }
      if (resData.status === "completed") {
        setProgress(100);
      }
    } catch (e) {
      console.error("Failed to fetch results", e);
    }
  };

  // ── Effects ──────────────────────────────────────────────────

  useEffect(() => {
    if (!query || hasStarted.current) return;
    hasStarted.current = true;

    void (async () => {
      if (isUrl(query)) {
        await fetchPreview(query);
      } else {
        await fetchHeadlines(query);
      }
    })();
  }, [query]);

  /* eslint-disable react-hooks/set-state-in-effect -- Sync status from task context */
  useEffect(() => {
    if (task?.status === "completed" && status !== "completed") {
      setStatus("completed");
    }
  }, [task, status]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!taskId) return;

    const wsUrl = `${API_BASE.replace("http", "ws")}/api/v1/ws/tasks/${taskId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setProgress(data.progress);
      setMessage(typeof data.message === "string" ? data.message : "");
      if (data.expected_duration_ms) setExpectedDurationMs(data.expected_duration_ms);

      if (data.warnings?.length) {
        setWarnings(data.warnings);
      }

      if (data.status === "completed") {
        fetchResults(taskId);
      } else if (data.status === "redirected") {
        const existingTaskId = data.progress_message || data.message;
        if (existingTaskId) {
          router.replace(`/search?taskId=${existingTaskId}`);
        }
      } else if (data.status === "failed") {
        let errMsg = "Error durante el análisis";
        if (typeof data.error_message === "string") {
          errMsg = data.error_message;
        } else if (typeof data.message === "string") {
          errMsg = data.message;
        }
        recoverToHeadlines(selectedHeadline?.source_url, errMsg);
      }
    };

    return () => { ws.close(); };
  }, [taskId]);

  useEffect(() => {
    if (initialTaskId) {
      void (async () => {
        await fetchResults(initialTaskId);
        addTask(initialTaskId, query || "Analizando noticia...");
      })();
    }
  }, [initialTaskId]);

  // ── Event Handlers ───────────────────────────────────────────

  const handleHeadlineConfirm = (headline: ArticlePreview) => {
    setPendingHeadline(null);
    startSearch(headline.source_url, headline);
  };

  // ── Render ───────────────────────────────────────────────────

  // Build display article for header
  const displayArticle = task?.source_article
    ? { ...selectedHeadline, ...task.source_article }
    : selectedHeadline;

  const showHeader = status !== "idle" && status !== "error" && status !== "headlines_selection" && status !== "headlines_loading";

  return (
    <div className="animate-fade-in max-w-5xl mx-auto">
      {/* ── Headline Confirmation Modal ────────────────── */}
      {pendingHeadline && (
        <HeadlineConfirmModal
          headline={pendingHeadline}
          onConfirm={handleHeadlineConfirm}
          onCancel={() => setPendingHeadline(null)}
          t={t}
        />
      )}

      {/* ── Header ─────────────────────────────────────── */}
      {showHeader && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-8 w-1 rounded-full bg-gradient-to-b from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-500" />
            {task?.status === "completed" && task.source_article ? (
              <h1 className="font-display text-3xl font-bold leading-tight text-gray-900 dark:text-white/90 transition-colors">
                {task.source_article.title}
              </h1>
            ) : (
              <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white transition-colors">{t.search.title}</h1>
            )}
          </div>

          {task?.status === "completed" && task.source_article ? (
            <div className="pl-[1.4rem] mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-2">
                <span className="text-teal-700 dark:text-teal-400 font-medium">{task.source_article.source_name}</span>
                {task.source_article.source_url && (
                  <a href={task.source_article.source_url} target="_blank" rel="noopener noreferrer" className="opacity-60 hover:opacity-100 text-gray-700 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-opacity">
                    🔗 {new URL(task.source_article.source_url).hostname}
                  </a>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full bg-gray-200 dark:bg-white/10 text-xs text-gray-700 dark:text-gray-300">{t.search.completed}</span>
              </div>
            </div>
          ) : (
            (() => {
              if (displayArticle) {
                return (
                  <div className="pl-[1.4rem] mt-2">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1 leading-snug transition-colors">{displayArticle.title}</h2>
                    <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 transition-colors">
                      <span className="text-teal-600 dark:text-teal-400 font-medium transition-colors">{displayArticle.source_name}</span>
                      {displayArticle.source_url && (
                        <a href={displayArticle.source_url} target="_blank" rel="noopener noreferrer" className="opacity-60 hover:opacity-100 text-gray-700 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-opacity">
                          🔗 {new URL(displayArticle.source_url).hostname}
                        </a>
                      )}
                      {displayArticle.published_at && (
                        <span>{new Date(displayArticle.published_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                );
              }
              return (
                <p className="mt-2 text-gray-500 dark:text-gray-400 pl-[1.4rem]">
                  Tema: <span className="text-teal-700 dark:text-teal-400 font-medium break-all">&quot;{task?.source_article?.title || task?.query || query}&quot;</span>
                  {task?.source_article?.source_url && (
                    <a href={task.source_article.source_url} target="_blank" rel="noopener noreferrer" className="ml-3 opacity-60 hover:opacity-100 text-gray-700 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-opacity break-all">
                      🔗 {new URL(task.source_article.source_url).hostname}
                    </a>
                  )}
                </p>
              );
            })()
          )}
        </div>
      )}

      {/* ── Warnings ───────────────────────────────────── */}
      <WarningBanner warnings={warnings} />

      {/* ── Progress ───────────────────────────────────── */}
      {(status === "starting" || status === "pending" || status === "scraping" || status === "analyzing") && (
        <SearchProgress
          status={status === "starting" ? "pending" : status}
          progress={displayProgress}
          expectedDurationMs={expectedDurationMs}
          message={message}
        />
      )}

      {/* ── Preview Card ───────────────────────────────── */}
      {status === "preview" && previewData && (
        <ArticlePreviewCard
          previewData={previewData}
          onStartAnalysis={() => startSearch(query, previewData)}
          t={t}
        />
      )}

      {/* ── Headlines Grid ─────────────────────────────── */}
      {showHeadlines && (
        <HeadlineGrid
          headlines={headlines}
          query={query}
          isAmbiguous={isAmbiguous}
          failedUrls={failedHeadlineUrls}
          onSelect={(h) => setPendingHeadline(h)}
          onAnalyzeGlobal={() => startSearch(query)}
          t={t}
        />
      )}

      {/* ── Error Banner ───────────────────────────────── */}
      {(error || status === "failed") && (
        <div className="mb-8 rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
          <div className="flex gap-3 items-start">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="font-bold text-red-400 mb-1">Error en el análisis</h3>
              <p className="text-red-300/80 text-sm">
                {error || task?.error_message || "Error durante el procesamiento"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Results Tabs ───────────────────────────────── */}
      {task?.status === "completed" && (
        <ResultsTabs
          task={task}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          t={t}
        />
      )}
    </div>
  );
}

function SearchContentWrapper() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const taskIdParam = searchParams.get("taskId") || "";
  return <SearchContent key={`${q}-${taskIdParam}`} />;
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white dark:bg-[#0a0a0a] transition-colors flex items-center justify-center text-teal-600 dark:text-teal-400">Cargando...</div>}>
      <SearchContentWrapper />
    </Suspense>
  );
}