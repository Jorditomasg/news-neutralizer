"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { SearchTask, ArticlePreview } from "@/types";
import { SearchProgress } from "@/components/search/SearchProgress";
import { SearchForm } from "@/components/search/SearchForm";
import { FeedbackButtons } from "@/components/feedback/FeedbackButtons";
import { useTaskContext } from "@/context/TaskContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const initialTaskId = searchParams.get("taskId");
  const { addTask } = useTaskContext();
  const router = useRouter();
  const [taskId, setTaskId] = useState<string | null>(initialTaskId);
  const [status, setStatus] = useState<string>(initialTaskId ? "pending" : "idle");
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [message, setMessage] = useState("");
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

  const isUrl = (text: string) => {
    return text.startsWith("http://") || text.startsWith("https://");
  };

  useEffect(() => {
    if (!query || hasStarted.current) return;
    hasStarted.current = true;

    if (isUrl(query)) {
      fetchPreview(query);
    } else {
      fetchHeadlines(query);
    }
  }, [query]);

  useEffect(() => {
    if (task?.status === "completed" && status !== "completed") {
      setStatus("completed");
      setDisplayProgress(100);
    }
  }, [task, status]);

  useEffect(() => {
    if (status === "completed" || status === "failed") {
      setDisplayProgress(progress);
      return;
    }

    const timer = setInterval(() => {
      setDisplayProgress((prev) => {
        if (prev >= progress) {
          const cap = status === "analyzing" ? 95 : 90;
          if (prev < cap && (status === "scraping" || status === "analyzing")) {
            return prev + 0.05;
          }
          return prev;
        }
        const diff = progress - prev;
        const step = Math.max(diff * 0.1, 0.5);
        return Math.min(prev + step, progress);
      });
    }, 50);

    return () => clearInterval(timer);
  }, [progress, status]);

  useEffect(() => {
    if (status === "starting") setDisplayProgress(0);
  }, [status]);

  const fetchHeadlines = async (searchQuery: string) => {
    try {
      setStatus("headlines_loading");
      const res = await fetch(`${API_BASE}/api/v1/search/headlines`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!res.ok) throw new Error("Failed to fetch headlines");

      const data = await res.json();
      if (data && data.length > 0) {
        setHeadlines(data);
        setShowHeadlines(true);
        setStatus("headlines_selection");
      } else {
        startSearch(searchQuery);
      }
    } catch (e) {
      console.warn("Headlines fetch failed, falling back to direct search", e);
      startSearch(searchQuery);
    }
  };

  const fetchPreview = async (url: string) => {
    try {
      setStatus("preview");
      const res = await fetch(`${API_BASE}/api/v1/search/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) throw new Error("Failed to fetch preview");

      const data: ArticlePreview = await res.json();
      setPreviewData(data);
    } catch (e) {
      console.error("Preview failed, falling back to direct search", e);
      startSearch(url);
    }
  };

  const _recoverToHeadlines = (failedUrl?: string, errorMsg?: string) => {
    // If we have headlines to go back to, show them with a warning
    if (headlines.length > 0) {
      if (failedUrl) {
        setFailedHeadlineUrls(prev => new Set(prev).add(failedUrl));
      }
      setError(errorMsg || null);
      setStatus("headlines_selection");
      setShowHeadlines(true);
      setTaskId(null);
      setTask(null);
      setProgress(0);
      setDisplayProgress(0);
      setMessage("");
      setSelectedHeadline(null);
    } else {
      // No headlines to recover to — show error inline
      setError(errorMsg || "Error durante el procesamiento");
      setStatus("error");
    }
  };

  const startSearch = async (searchQuery: string, headline?: ArticlePreview) => {
    try {
      setStatus("starting");
      setError(null);
      setPreviewData(null);
      setShowHeadlines(false);
      if (headline) {
        setSelectedHeadline(headline);
      } else {
        setSelectedHeadline(null);
      }

      const payload: any = { query: searchQuery };
      if (headline && !isUrl(query)) {
        payload.original_query = query;
      }

      const res = await fetch(`${API_BASE}/api/v1/search/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        // Check for ambiguous topic error
        if (res.status === 400 && errorData.detail && typeof errorData.detail === 'string' && errorData.detail.includes("AMBIGUOUS_TOPIC")) {
          const reason = errorData.detail.replace("AMBIGUOUS_TOPIC: ", "");
          setIsAmbiguous(true);
          setError(`Tema demasiado amplio: ${reason}. Por favor, selecciona una noticia concreta de la lista.`);
          setStatus("headlines_selection");
          setShowHeadlines(true);
          return;
        }
        // Stringify the error detail safely (fixes [Object Object])
        const errorDetail = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail) || "Error desconocido del servidor";
        throw new Error(errorDetail);
      }

      const data = await res.json();
      setTaskId(data.task_id);
      addTask(data.task_id, headline ? headline.title : query || "Analizando noticia...");
      setStatus("pending");
    } catch (e: any) {
      if (!isAmbiguous) {
        const errorMsg = typeof e.message === 'string' ? e.message : "No se pudo iniciar la búsqueda. ¿Está el backend corriendo?";
        _recoverToHeadlines(headline?.source_url, errorMsg);
      }
      hasStarted.current = false;
    }
  };

  useEffect(() => {
    if (!taskId) return;

    const wsUrl = `${API_BASE.replace("http", "ws")}/api/v1/ws/tasks/${taskId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setProgress(data.progress);
      setMessage(typeof data.message === 'string' ? data.message : '');

      if (data.status === "completed") {
        fetchResults(taskId);
      } else if (data.status === "failed") {
        const errMsg = typeof data.error_message === 'string' ? data.error_message 
          : typeof data.message === 'string' ? data.message : "Error durante el análisis";
        _recoverToHeadlines(selectedHeadline?.source_url, errMsg);
      }
    };

    ws.onerror = () => {
      pollResults(taskId);
    };

    return () => {
      ws.close();
    };
  }, [taskId]);

  const fetchResults = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/search/${id}`);
      if (res.ok) {
        const data = await res.json();
        setTask(data);
        setStatus(data.status);
        if (data.status === "completed") {
            setProgress(100);
            setDisplayProgress(100);
        }
      }
    } catch (e) {
      console.error("Failed to fetch results", e);
    }
  };

  // If initialTaskId is present (reload/navigation), reconnect to the task
  useEffect(() => {
      if (initialTaskId) {
          // Fetch current state from API
          fetchResults(initialTaskId).then(() => {
            // Re-register in TaskContext so GlobalTaskTracker reconnects WebSocket
            addTask(initialTaskId, query || "Analizando noticia...");
          });
      }
  }, [initialTaskId]);

  const pollResults = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/search/${id}`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data.status);
          setProgress(data.progress);
          if (data.progress_message || data.error_message) {
              setMessage(data.progress_message || data.error_message);
          }
          if (data.status === "completed") {
            setTask(data);
            clearInterval(interval);
          } else if (data.status === "failed") {
            clearInterval(interval);
            const errMsg = typeof data.error_message === 'string' ? data.error_message : "Error durante el análisis";
            _recoverToHeadlines(selectedHeadline?.source_url, errMsg);
          }
        }
      } catch (e) {
        clearInterval(interval);
      }
    }, 3000);
  };

  const getProgressLabel = () => {
    if (message) return message;

    switch (status) {
      case "starting": return "Iniciando búsqueda...";
      case "pending": return "En cola de procesamiento...";
      case "scraping": return progress < 30 ? "Buscando artículos..." : "Procesando contenido...";
      case "analyzing": return "Analizando con IA...";
      default: return "Procesando...";
    }
  };

  const parseNeutralizedArticle = (text: string) => {
    if (!text) return { headline: "", lead: "", body: "" };
    const lines = text.split("\n").filter(l => l.trim());
    if (lines.length === 0) return { headline: "", lead: "", body: text };

    const headline = lines[0].replace(/^\[?TITULAR[:\s]*/i, "").replace(/\]$/, "").trim();
    const rest = lines.slice(1).join("\n\n");

    const paragraphs = rest.split("\n\n").filter(p => p.trim());
    const lead = paragraphs[0] || "";
    const body = paragraphs.slice(1).join("\n\n");

    return { headline, lead, body };
  };

  const getBiasColor = (score: number) => {
    if (score < 0.3) return { bg: "bg-emerald-500/10", text: "text-emerald-400", bar: "bg-emerald-500" };
    if (score < 0.6) return { bg: "bg-amber-500/10", text: "text-amber-400", bar: "bg-amber-500" };
    return { bg: "bg-red-500/10", text: "text-red-400", bar: "bg-red-500" };
  };

  const getSeverityLabel = (severity: number) => {
    const labels = ["", "Muy sutil", "Sutil", "Moderado", "Notable", "Grave"];
    return labels[severity] || "Moderado";
  };

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case "izquierda": return "←";
      case "derecha": return "→";
      case "centro": return "◆";
      case "sensacionalista": return "⚡";
      default: return "•";
    }
  };

  const handleSearch = (q: string) => {
    if (isUrl(q)) fetchPreview(q);
    else fetchHeadlines(q);
  };

  return (
    <div className="animate-fade-in max-w-5xl mx-auto">

      {/* ── Headline Confirmation Modal ──────────────────────── */}
      {pendingHeadline && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setPendingHeadline(null)}
          />
          {/* Modal */}
          <div className="relative w-full max-w-xl rounded-2xl border border-white/10 bg-[#111] shadow-2xl shadow-black/60 p-7 animate-fade-in">
            {/* Header */}
            <div className="flex items-start gap-3 mb-5">
              <div className="shrink-0 mt-0.5 h-8 w-8 rounded-full bg-teal-500/20 flex items-center justify-center">
                <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-widest text-teal-400 mb-1">Noticia seleccionada</p>
                <h2 className="text-lg font-bold text-white leading-snug">{pendingHeadline.title}</h2>
              </div>
            </div>

            {/* Meta */}
            <div className="flex flex-wrap gap-3 mb-6 text-sm text-gray-400">
              <div className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/5 px-3 py-2">
                <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Fuente</span>
                <span className="font-semibold text-white">{pendingHeadline.source_name}</span>
              </div>
              {pendingHeadline.published_at && (
                <div className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/5 px-3 py-2">
                  <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Fecha</span>
                  <span>{new Date(pendingHeadline.published_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
                </div>
              )}
            </div>

            {/* URL preview */}
            <div className="mb-7 rounded-lg bg-white/[0.03] border border-white/5 px-4 py-2.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">Enlace</p>
              <a
                href={pendingHeadline.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-teal-400/80 hover:text-teal-300 truncate block transition-colors"
              >
                {pendingHeadline.source_url.length > 80
                  ? pendingHeadline.source_url.slice(0, 80) + '…'
                  : pendingHeadline.source_url}
              </a>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  const h = pendingHeadline;
                  setPendingHeadline(null);
                  startSearch(h.source_url, h);
                }}
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-gray-950 font-bold text-sm transition-all shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 active:scale-95"
              >
                🚀 Continuar análisis
              </button>
              <button
                onClick={() => setPendingHeadline(null)}
                className="flex-1 py-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-gray-300 font-semibold text-sm transition-all active:scale-95"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
      {(status === "idle" || status === "error") && (
        <div className="flex flex-col items-center text-center py-12 mb-8">
          <h1 className="text-4xl font-display font-bold tracking-tight text-white sm:text-6xl mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white via-gray-200 to-gray-400">
            Descubre la verdad <br />
            <span className="text-teal-400">detrás de las noticias</span>
          </h1>
          <p className="mt-4 text-lg leading-8 text-gray-400 max-w-2xl mx-auto mb-10">
            Analiza noticias con IA para detectar sesgos, comparar fuentes y obtener
            resúmenes neutrales en segundos.
          </p>
          <SearchForm onSearch={handleSearch} isLoading={false} />
        </div>
      )}

      {/* Header - Show during Progress, Results, and Preview */}
      {(status !== "idle" && status !== "error" && status !== "headlines_selection" && status !== "headlines_loading") && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-8 w-1 rounded-full bg-gradient-to-b from-teal-400 to-cyan-500" />
            {task?.status === "completed" && task.source_article ? (
              <h1 className="font-display text-3xl font-bold leading-tight text-white/90">
                {task.source_article.title}
              </h1>
            ) : (
              <h1 className="font-display text-3xl font-bold">Análisis de noticias</h1>
            )}
          </div>

          {task?.status === "completed" && task.source_article ? (
            <div className="pl-[1.4rem] mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <span className="text-teal-400 font-medium">{task.source_article.source_name}</span>
                {task.source_article.source_url && (
                  <a href={task.source_article.source_url} target="_blank" rel="noopener noreferrer" className="opacity-60 hover:opacity-100 hover:text-white transition-opacity">
                    🔗 {new URL(task.source_article.source_url).hostname}
                  </a>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full bg-white/10 text-xs text-gray-300">Análisis completado</span>
              </div>
            </div>
          ) : selectedHeadline ? (
            <div className="pl-[1.4rem] mt-2">
              <h2 className="text-xl font-bold text-white mb-1 leading-snug">{selectedHeadline.title}</h2>
              <div className="flex items-center gap-3 text-sm text-gray-400">
                <span className="text-teal-400 font-medium">{selectedHeadline.source_name}</span>
                {selectedHeadline.published_at && (
                  <span>{new Date(selectedHeadline.published_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          ) : (
            <p className="mt-2 text-gray-400 pl-[1.4rem]">
              Tema: <span className="text-teal-400 font-medium">&quot;{task?.source_article?.title || task?.query || query}&quot;</span>
            </p>
          )}
        </div>
      )}

      {/* Integrated Progress UI - Below Header */}
      {(status === "starting" || status === "pending" || status === "scraping" || status === "analyzing") && (
        <SearchProgress
          status={status === "starting" ? "pending" : status}
          progress={progress}
          message={message}
        />
      )}

      {status === "preview" && previewData && (
        <div className="mb-10 rounded-2xl border border-blue-500/20 bg-blue-500/5 p-8 backdrop-blur-sm animate-fade-in relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <span className="text-9xl">📰</span>
          </div>

          <div className="relative z-10">
            <h3 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-3">Artículo Detectado</h3>
            <h2 className="text-2xl font-bold text-white mb-4 leading-tight max-w-3xl">
              {previewData.title}
            </h2>

            <div className="flex flex-wrap gap-4 text-sm text-gray-300 mb-8">
              <div className="flex items-center gap-2">
                <span className="bg-white/10 px-2 py-1 rounded text-xs text-gray-400 uppercase font-bold tracking-wider">Fuente</span>
                <span className="font-medium text-white">{previewData.source_name}</span>
              </div>
              {previewData.author && (
                <div className="flex items-center gap-2">
                  <span className="bg-white/10 px-2 py-1 rounded text-xs text-gray-400 uppercase font-bold tracking-wider">Autor</span>
                  <span>{previewData.author}</span>
                </div>
              )}
              {previewData.published_at && (
                <div className="flex items-center gap-2">
                  <span className="bg-white/10 px-2 py-1 rounded text-xs text-gray-400 uppercase font-bold tracking-wider">Fecha</span>
                  <span>{new Date(previewData.published_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => startSearch(query, previewData)}
                className="px-6 py-3 rounded-xl bg-blue-500 hover:bg-blue-400 text-white font-bold shadow-lg shadow-blue-500/20 transition-all transform hover:scale-105 active:scale-95 flex items-center gap-2"
              >
                <span>🚀</span>
                <span>Analizar este artículo</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {showHeadlines && headlines.length > 0 && (
        <div className="animate-fade-in space-y-6 mb-12">
          <div className="rounded-2xl border border-teal-500/20 bg-teal-500/5 p-6 backdrop-blur-sm">
            <div className="flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white mb-2">¿Qué quieres analizar?</h2>
                <p className="text-gray-400 text-sm">
                  Hemos encontrado varias noticias recientes sobre <span className="text-teal-400">&quot;{query}&quot;</span>.
                  <br />Selecciona una noticia específica o analiza el tema en general.
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                {!isAmbiguous ? (
                  <button
                    onClick={() => startSearch(query)}
                    className="whitespace-nowrap px-6 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-600 hover:from-teal-400 hover:to-cyan-500 text-white font-bold shadow-lg shadow-teal-500/20 transition-all transform hover:scale-105 active:scale-95 ring-1 ring-white/20"
                  >
                    ⚡ Analizar Tema Global
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
            {headlines.map((headline, idx) => {
              const isFailed = failedHeadlineUrls.has(headline.source_url);
              return (
                <button
                  key={idx}
                  onClick={() => setPendingHeadline(headline)}
                  className={`text-left group relative flex flex-col justify-between h-full rounded-xl border p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-teal-900/10 ${
                    isFailed
                      ? 'border-amber-500/30 bg-amber-500/[0.04] hover:bg-amber-500/[0.07]'
                      : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-teal-500/30'
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
                    <h3 className="font-bold text-gray-200 group-hover:text-white mb-3 line-clamp-3 leading-snug">
                      {headline.title}
                    </h3>
                  </div>
                  <div className="mt-4 flex items-center text-xs font-medium text-gray-500 group-hover:text-teal-400 transition-colors">
                    <span>{isFailed ? 'Reintentar análisis' : 'Analizar esta noticia'}</span>
                    <svg className="w-3 h-3 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}



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

      {task && task.status === "completed" && (
        <div className="space-y-6">
          <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/10">
            {([
              { key: "article" as const, label: "📝 Artículo neutral", icon: "" },
              { key: "bias" as const, label: "🎯 Sesgo detectado", icon: "" },
              { key: "sources" as const, label: "📊 Posibles Fuentes", icon: "" },
            ]).map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key
                    ? "bg-gradient-to-r from-teal-500/20 to-cyan-500/20 text-white border border-teal-500/30"
                    : "text-gray-400 hover:text-gray-300 hover:bg-white/[0.03]"
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "article" && task.analysis && (
            <div className="space-y-6 animate-fade-in">
              <div className="rounded-2xl border border-teal-500/20 bg-gradient-to-br from-teal-500/5 to-cyan-500/5 p-6">
                <div className="flex items-center gap-2 mb-3">
                  <div className="h-5 w-5 rounded-full bg-teal-400/20 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-teal-400" />
                  </div>
                  <span className="text-xs font-medium text-teal-400 tracking-wider uppercase">Resumen del tema</span>
                </div>
                <p className="text-gray-200 leading-relaxed text-lg">
                  {task.analysis.topic_summary}
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
                <div className="border-b border-white/10 px-6 py-4 bg-white/[0.02]">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">✍️</span>
                    <h2 className="font-display text-lg font-bold text-white">
                      Artículo neutral
                    </h2>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Generado por IA a partir de {task.articles.length} fuentes · {task.analysis.provider_used}
                  </p>
                </div>
                <div className="p-6 md:p-8">
                  {(() => {
                    const { headline, lead, body } = parseNeutralizedArticle(task.analysis.neutralized_summary);
                    return (
                      <article className="prose-custom">
                        {headline && (
                          <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-4 leading-tight">
                            {headline}
                          </h2>
                        )}
                        {lead && (
                          <p className="text-gray-300 text-lg leading-relaxed mb-6 font-medium border-l-2 border-teal-500/40 pl-4">
                            {lead.replace(/^\[?ENTRADILLA[:\s]*/i, "").replace(/\]$/, "")}
                          </p>
                        )}
                        {body ? (
                          body.split("\n\n").map((paragraph, i) => (
                            <p key={i} className="text-gray-300 leading-relaxed mb-4">
                              {paragraph.replace(/^\[?CUERPO[:\s]*/i, "").replace(/^\[?CONCLUSI[ÓO]N[:\s]*/i, "").replace(/\]$/, "")}
                            </p>
                          ))
                        ) : (
                          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                            {task.analysis.neutralized_summary}
                          </p>
                        )}
                      </article>
                    );
                  })()}
                </div>
                {/* Feedback Widget for the Overall Analysis */}
                <div className="border-t border-white/10 px-6 py-4 bg-white/[0.01] flex justify-end">
                  <FeedbackButtons targetType="analysis" targetId={task.task_id} />
                </div>
              </div>

              {task.analysis.objective_facts.length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">📋</span>
                    <h2 className="font-display text-lg font-bold">Hechos verificados</h2>
                    <span className="ml-auto rounded-full bg-teal-500/10 px-2.5 py-0.5 text-xs font-medium text-teal-400">
                      {task.analysis.objective_facts.length}
                    </span>
                  </div>
                  <div className="grid gap-2">
                    {task.analysis.objective_facts.map((fact, i) => (
                      <div key={i} className="flex gap-3 items-start rounded-xl bg-white/[0.02] p-3 border border-white/5">
                        <span className="shrink-0 mt-0.5 h-5 w-5 rounded-full bg-teal-500/10 flex items-center justify-center text-xs font-bold text-teal-400">
                          {i + 1}
                        </span>
                        <span className="text-gray-300 text-sm leading-relaxed">{fact}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "bias" && task.analysis && (
            <div className="space-y-4 animate-fade-in">
              {task.analysis.bias_elements.length > 0 ? (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-gray-400">
                      Se detectaron <span className="text-white font-medium">{task.analysis.bias_elements.length}</span> elementos de sesgo
                    </p>
                  </div>
                  {task.analysis.bias_elements.map((bias, i) => (
                    <div
                      key={i}
                      className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden transition-all hover:border-white/20"
                    >
                      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5 bg-white/[0.01]">
                        <span className={`rounded-lg px-2.5 py-1 text-xs font-bold tracking-wide uppercase ${bias.type === "sensacionalismo" ? "bg-red-500/10 text-red-400" :
                            bias.type === "omisión" ? "bg-purple-500/10 text-purple-400" :
                              bias.type === "framing" ? "bg-amber-500/10 text-amber-400" :
                                bias.type === "adjetivación" ? "bg-orange-500/10 text-orange-400" :
                                  "bg-pink-500/10 text-pink-400"
                          }`}>
                          {bias.type}
                        </span>
                        <span className="text-xs text-gray-500">en</span>
                        <span className="text-sm font-medium text-gray-300">{bias.source}</span>
                        <div className="flex gap-1 ml-auto items-center">
                          <span className="text-xs text-gray-500 mr-1">{getSeverityLabel(bias.severity)}</span>
                          {Array.from({ length: 5 }).map((_, j) => (
                            <div
                              key={j}
                              className={`h-2.5 w-2.5 rounded-sm transition-all ${j < bias.severity
                                  ? bias.severity >= 4 ? "bg-red-400" : bias.severity >= 3 ? "bg-amber-400" : "bg-yellow-400/60"
                                  : "bg-white/10"
                                }`}
                            />
                          ))}
                        </div>
                      </div>
                      <div className="px-5 py-4 space-y-3">
                        <blockquote className="text-sm text-gray-400 italic border-l-2 border-amber-500/30 pl-4 py-1">
                          &quot;{bias.original_text}&quot;
                        </blockquote>
                        <p className="text-sm text-gray-300 leading-relaxed">
                          <span className="text-teal-400 font-medium">Análisis: </span>
                          {bias.explanation}
                        </p>
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 text-center">
                  <span className="text-4xl mb-3 block">✅</span>
                  <p className="text-gray-300">No se detectaron elementos de sesgo significativos</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "sources" && (
            <div className="space-y-6 animate-fade-in">
              {task.analysis && Object.keys(task.analysis.source_bias_scores).length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                  <div className="flex items-center gap-2 mb-5">
                    <span className="text-lg">📊</span>
                    <h2 className="font-display text-lg font-bold">Comparación de sesgo por fuente</h2>
                  </div>
                  <div className="space-y-4">
                    {Object.entries(task.analysis.source_bias_scores)
                      .sort(([, a], [, b]) => (b.score || 0) - (a.score || 0))
                      .map(([source, scores]) => {
                        const color = getBiasColor(scores.score);
                        return (
                          <div key={source} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-2">
                                <span className="text-base">{getDirectionIcon(scores.direction)}</span>
                                <span className="font-medium text-white">{source}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <FeedbackButtons targetType="domain" targetId={source} compact />
                                <div className="flex items-center gap-2">
                                  <span className={`rounded-lg px-2 py-0.5 text-xs font-medium capitalize ${color.bg} ${color.text}`}>
                                    {scores.direction}
                                  </span>
                                  <span className={`font-mono text-sm font-bold ${color.text}`}>
                                    {(scores.score * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                              <div
                                className={`h-full rounded-full ${color.bar} transition-all duration-700`}
                                style={{ width: `${scores.score * 100}%` }}
                              />
                            </div>
                            <div className="flex justify-between mt-1.5">
                              <span className="text-[10px] text-gray-600">Neutral</span>
                              <span className="text-[10px] text-gray-600">Confianza: {((scores.confidence || 0) * 100).toFixed(0)}%</span>
                              <span className="text-[10px] text-gray-600">Máx. sesgo</span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}

              {task.articles.length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">📰</span>
                    <h2 className="font-display text-lg font-bold">Artículos relacionados</h2>
                    <span className="ml-auto rounded-full bg-white/5 px-2.5 py-0.5 text-xs font-medium text-gray-400">
                      {task.articles.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {task.articles.map((article) => {
                      const isAnalyzed = article.status === 'ANALYZED' || article.status === 'CONTEXTUALIZED';
                      return (
                        <div
                          key={article.id}
                          className="flex items-center gap-4 rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-all hover:border-teal-500/20 hover:bg-white/[0.04] group"
                        >
                          <div className="min-w-0 flex-1">
                            <a
                              href={article.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-white truncate block group-hover:text-teal-300 transition-colors"
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
                            <span className="shrink-0 rounded-md bg-blue-500/20 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-blue-300 ring-1 ring-inset ring-blue-500/30">
                              Base
                            </span>
                          )}

                          {isAnalyzed ? (
                            <span className="shrink-0 rounded-md bg-teal-500/20 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-teal-300 ring-1 ring-inset ring-teal-500/30 flex items-center gap-1">
                              ✅ Analizado
                            </span>
                          ) : (
                            <span className={`shrink-0 rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider ring-1 ring-inset ${
                              article.status === 'DETECTING' || article.status === 'DETECTED' ? 'bg-gray-500/20 text-gray-300 ring-gray-500/30' :
                              article.status === 'ANALYZING' ? 'bg-amber-500/20 text-amber-300 ring-amber-500/30' :
                              'bg-gray-500/20 text-gray-300 ring-gray-500/30'
                            }`}>
                              {article.status === 'DETECTED' ? 'Detectado' :
                               article.status === 'ANALYZING' ? 'Analizando...' :
                               article.status || 'Detectado'}
                            </span>
                          )}

                          {article.bias_score !== null && article.bias_score !== undefined && (
                            <div className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-mono font-bold ${getBiasColor(article.bias_score).bg} ${getBiasColor(article.bias_score).text}`}>
                              {(article.bias_score * 100).toFixed(0)}%
                            </div>
                          )}

                          {/* Analizar button — only for non-source, non-analyzed articles */}
                          {!article.is_source && !isAnalyzed && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/search?q=${encodeURIComponent(article.source_url)}`);
                              }}
                              className="shrink-0 rounded-lg bg-gradient-to-r from-teal-500/80 to-cyan-500/80 px-3 py-1.5 text-[11px] font-bold text-gray-950 transition-all hover:from-teal-400 hover:to-cyan-400 hover:shadow-md hover:shadow-teal-500/20 active:scale-95"
                            >
                              🔍 Analizar
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
          )}

          {!task.analysis && task.articles.length > 0 && (
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6">
              <div className="flex gap-3 items-start">
                <span className="text-2xl">⏳</span>
                <div>
                  <h3 className="font-bold text-amber-400 mb-1">Artículos encontrados sin análisis</h3>
                  <p className="text-amber-300/70 text-sm">
                    Se encontraron {task.articles.length} artículos pero el análisis de IA no se completó.
                    Verifica que Ollama esté corriendo y el modelo descargado.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center text-teal-400">Cargando...</div>}>
      <SearchContent />
    </Suspense>
  );
}