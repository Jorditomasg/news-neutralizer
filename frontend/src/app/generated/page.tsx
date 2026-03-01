"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiClient } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GeneratedNewsOut {
  id: number;
  title: string;
  lead: string;
  body: string;
  context_articles_ids: number[];
  reliability_score_achieved: number | null;
  has_new_context_available: boolean;
  created_at: string;
}

interface PaginatedGeneratedNews {
  total: number;
  page: number;
  page_size: number;
  items: GeneratedNewsOut[];
}

export default function GeneratedNewsPage() {
  const [data, setData] = useState<PaginatedGeneratedNews | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState(""); // Optionally implement search in backend later
  const { t } = useI18n();

  const fetchNews = async (p: number) => {
    try {
      setLoading(true);
      setError(null);
      const url = `/api/v1/generate/?page=${p}&page_size=15`;
      const data = await apiClient(url);
      setData(data as PaginatedGeneratedNews);
    } catch (e: any) {
      setError(e.message || "Failed to load generated news");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews(page);
  }, [page]);

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="h-8 w-1 rounded-full bg-gradient-to-b from-purple-500 to-pink-500 dark:from-purple-400 dark:to-pink-500" />
        <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white transition-colors">
          {t?.generated.title}
        </h1>
      </div>

      {error ? (
        <div className="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 p-4 rounded-xl border border-red-200 dark:border-red-500/20 transition-colors">
          {error}
        </div>
      ) : loading && !data ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
             <div key={i} className="h-24 bg-gray-100 dark:bg-white/5 animate-pulse rounded-xl border border-gray-200 dark:border-white/5 transition-colors"></div>
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-xl transition-colors">
          {t?.generated.no_news}
        </div>
      ) : (
        <div className="space-y-4">
          {data?.items.map((item) => (
            <Link 
              href={`/generated/${item.id}`} 
              key={item.id}
              className="block relative bg-white dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 rounded-xl p-5 hover:bg-gray-50 dark:hover:bg-white/[0.05] hover:border-purple-300 dark:hover:border-purple-500/30 transition-all group overflow-hidden shadow-sm dark:shadow-none"
            >
              {/* Highlight badge for new context */}
              {item.has_new_context_available && (
                  <div className="absolute top-0 right-0 pt-2 pr-3">
                      <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-semibold bg-gradient-to-r from-orange-100 to-red-100 dark:from-orange-500/20 dark:to-red-500/20 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-500/30 shadow-sm animate-pulse-slow">
                          <span className="w-1.5 h-1.5 rounded-full bg-orange-500 dark:bg-orange-400" />
                          {t?.generated.new_context}
                      </span>
                  </div>
              )}

              <div className="flex-1 min-w-0 pr-4 mt-2 sm:mt-0">
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-200 group-hover:text-purple-600 dark:group-hover:text-white mb-2 leading-tight transition-colors">
                  {item.title}
                </h2>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2 leading-relaxed transition-colors">
                  {item.lead}
                </p>
                
                <div className="flex flex-wrap items-center justify-between text-xs text-gray-500 gap-y-3 transition-colors">
                  <div className="flex flex-wrap gap-4">
                      {item.reliability_score_achieved !== null && (
                          <span className="flex items-center gap-1 font-medium bg-gray-100 dark:bg-white/5 px-2 py-1 rounded-md transition-colors">
                            <svg className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span className="text-gray-700 dark:text-gray-300 transition-colors">
                                {t?.generated.factual_consensus}: <span className="text-purple-600 dark:text-purple-400 font-bold">{Math.round(item.reliability_score_achieved)}%</span>
                            </span>
                          </span>
                      )}
                      <span className="flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-gray-600"></span>
                          {t?.generated.based_on_sources.replace("{count}", item.context_articles_ids.length.toString())}
                      </span>
                  </div>
                  
                  <span className="flex items-center gap-1 text-purple-600 dark:text-purple-400 font-medium text-sm group-hover:text-purple-500 dark:group-hover:text-purple-300 transition-colors">
                    {t?.generated.read_report}
                    <svg className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </span>
                </div>
              </div>
            </Link>
          ))}
          
          {/* Pagination Controls */}
          {data && data.total > data.page_size && (
             <div className="flex justify-center gap-2 mt-8">
               <button 
                 onClick={() => setPage(p => Math.max(1, p - 1))}
                 disabled={page === 1}
                 className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-900 dark:text-white disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
               >
                 {t?.generated.prev}
               </button>
               <span className="px-4 py-2 text-gray-600 dark:text-gray-400 transition-colors">
                 {t?.generated.page.replace("{page}", page.toString()).replace("{total}", Math.ceil(data.total / data.page_size).toString())}
               </span>
               <button 
                 onClick={() => setPage(p => Math.min(Math.ceil(data.total / data.page_size), p + 1))}
                 disabled={page >= Math.ceil(data.total / data.page_size)}
                 className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-900 dark:text-white disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
               >
                 {t?.generated.next}
               </button>
             </div>
          )}
        </div>
      )}
    </div>
  );
}
