"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SearchTaskSummary } from "@/types";
import { apiClient } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PaginatedHistory {
  total: number;
  page: number;
  page_size: number;
  items: SearchTaskSummary[];
}

export default function AnalyzedPage() {
  const [data, setData] = useState<PaginatedHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const { t } = useI18n();

  const fetchHistory = async (p: number, q: string) => {
    try {
      setLoading(true);
      setError(null);
      const searchParams = new URLSearchParams();
      searchParams.append("page", p.toString());
      searchParams.append("page_size", "15");
      if (q) searchParams.append("query", q);

      const data = await apiClient(`/api/v1/history/?${searchParams.toString()}`);
      setData(data as PaginatedHistory);
    } catch (e: any) {
      setError(e.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchHistory(page, search);
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [page, search]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setPage(1); // Reset page on new search
  };

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="h-8 w-1 rounded-full bg-gradient-to-b from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-500" />
        <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white transition-colors">
          {t?.analyzed.title}
        </h1>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder={t?.analyzed.search_placeholder}
          value={search}
          onChange={handleSearchChange}
          className="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm dark:shadow-none focus:outline-none focus:ring-2 focus:ring-teal-500/50 dark:focus:ring-teal-400/50 focus:border-transparent transition-all"
        />
      </div>

      {error ? (
        <div className="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 p-4 rounded-xl border border-red-200 dark:border-red-500/20">
          {error}
        </div>
      ) : loading && !data ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
             <div key={i} className="h-24 bg-gray-100 dark:bg-white/5 animate-pulse rounded-xl border border-gray-200 dark:border-white/5"></div>
          ))}
        </div>
      ) : (
        <>
          {/* Generation Suggestion Banner */}
          {data && data.items.length >= 2 && (
            <div className="mb-6 p-5 rounded-2xl border border-teal-200 dark:border-teal-500/20 bg-gradient-to-r from-teal-50 via-cyan-50 to-teal-50 dark:from-teal-500/5 dark:via-cyan-500/5 dark:to-teal-500/5 backdrop-blur-xl transition-colors">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 dark:bg-teal-500/10 text-xl shrink-0 transition-colors">
                    ✨
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white transition-colors">
                      {t?.analyzed.suggestion_title.replace("{count}", data.items.length.toString())}
                    </h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors">
                      {t?.analyzed.suggestion_desc}
                    </p>
                  </div>
                </div>
                <Link
                  href="/generated"
                  className="shrink-0 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-400 text-white dark:text-gray-950 text-sm font-bold hover:shadow-lg hover:shadow-teal-500/25 transition-all"
                >
                  {t?.analyzed.generate_btn}
                </Link>
              </div>
            </div>
          )}

          {data?.items.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400 bg-white dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-xl shadow-sm dark:shadow-none transition-colors">
              {t?.analyzed.no_history}
            </div>
          ) : (
            <div className="space-y-4">
              {data?.items.map((item) => (
                <Link 
                  href={`/search?taskId=${item.task_id}`} 
                  key={item.task_id}
                  className="block bg-white dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-xl p-5 hover:bg-gray-50 dark:hover:bg-white/[0.05] hover:border-teal-300 dark:hover:border-teal-500/30 shadow-sm hover:shadow-md dark:shadow-none transition-all flex items-center justify-between group"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <h2 className="text-lg font-bold text-gray-900 dark:text-gray-200 dark:group-hover:text-white mb-2 leading-tight truncate transition-colors">
                      {item.title || item.query || item.source_url}
                    </h2>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-500">
                      {item.source_name && (
                        <span className="flex items-center gap-1 font-medium text-gray-600 dark:text-gray-300 transition-colors">
                          <svg className="w-3.5 h-3.5 text-teal-600 dark:text-teal-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2m-2-1m-4 5V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h4" />
                          </svg>
                          <span className="truncate max-w-[150px] sm:max-w-xs">{item.source_name}</span>
                        </span>
                      )}
                      <span className="flex items-center gap-1 shrink-0">
                        <span className="w-2 h-2 rounded-full bg-teal-500 dark:bg-teal-400 hidden sm:inline-block"></span>
                        {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                      </span>
                      <span className="shrink-0">
                        {t?.analyzed.model}<span className="text-teal-600 dark:text-teal-400 font-medium">{item.provider_used || t?.analyzed.unknown}</span>
                      </span>
                    </div>
                  </div>
                  <div className="ml-4 shrink-0">
                    <span className="flex items-center gap-1 text-teal-600 dark:text-teal-400 font-medium text-sm transition-colors">
                      {t?.analyzed.view_details}
                      <svg className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </span>
                  </div>
                </Link>
              ))}
              
              {/* Pagination Controls */}
              {data && data.total > data.page_size && (
                 <div className="flex justify-center gap-2 mt-8">
                   <button 
                     onClick={() => setPage(p => Math.max(1, p - 1))}
                     disabled={page === 1}
                     className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-white shadow-sm dark:shadow-none disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
                   >
                     {t?.analyzed.prev}
                   </button>
                   <span className="px-4 py-2 text-gray-500 dark:text-gray-400">
                     {t?.analyzed.page.replace("{page}", page.toString()).replace("{total}", Math.ceil(data.total / data.page_size).toString())}
                   </span>
                   <button 
                     onClick={() => setPage(p => Math.min(Math.ceil(data.total / data.page_size), p + 1))}
                     disabled={page >= Math.ceil(data.total / data.page_size)}
                     className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-white shadow-sm dark:shadow-none disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
                   >
                     {t?.analyzed.next}
                   </button>
                 </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
