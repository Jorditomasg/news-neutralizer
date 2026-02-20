"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SearchTaskSummary } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PaginatedHistory {
  total: number;
  page: number;
  page_size: number;
  items: SearchTaskSummary[];
}

export default function HistoryPage() {
  const [data, setData] = useState<PaginatedHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const fetchHistory = async (p: number, q: string) => {
    try {
      setLoading(true);
      setError(null);
      const url = new URL(`${API_BASE}/api/v1/history/`);
      url.searchParams.append("page", p.toString());
      url.searchParams.append("page_size", "15");
      if (q) url.searchParams.append("query", q);

      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Error fetching history");
      
      const json = await res.json();
      setData(json);
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
        <div className="h-8 w-1 rounded-full bg-gradient-to-b from-teal-400 to-cyan-500" />
        <h1 className="font-display text-3xl font-bold text-white">
          Historial de Búsquedas
        </h1>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder="Buscar temas, URLs..."
          value={search}
          onChange={handleSearchChange}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-transparent transition-all"
        />
      </div>

      {error ? (
        <div className="text-red-400 bg-red-500/10 p-4 rounded-xl border border-red-500/20">
          {error}
        </div>
      ) : loading && !data ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
             <div key={i} className="h-24 bg-white/5 animate-pulse rounded-xl border border-white/5"></div>
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 text-gray-400 bg-white/[0.02] border border-white/5 rounded-xl">
          No se encontraron búsquedas en el historial.
        </div>
      ) : (
        <div className="space-y-4">
          {data?.items.map((item) => (
            <Link 
              href={`/search?taskId=${item.task_id}`} 
              key={item.task_id}
              className="block bg-white/[0.02] border border-white/5 rounded-xl p-5 hover:bg-white/[0.05] hover:border-teal-500/30 transition-all flex items-center justify-between group"
            >
              <div className="flex-1 min-w-0 pr-4">
                <h2 className="text-lg font-bold text-gray-200 group-hover:text-white mb-2 leading-tight truncate">
                  {item.title || item.query || item.source_url}
                </h2>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500">
                  {item.source_name && (
                    <span className="flex items-center gap-1 font-medium text-gray-300">
                      <svg className="w-3.5 h-3.5 text-teal-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2m-2-1m-4 5V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h4" />
                      </svg>
                      <span className="truncate max-w-[150px] sm:max-w-xs">{item.source_name}</span>
                    </span>
                  )}
                  <span className="flex items-center gap-1 shrink-0">
                    <span className="w-2 h-2 rounded-full bg-teal-500 hidden sm:inline-block"></span>
                    {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                  </span>
                  <span className="shrink-0">
                    Modelo: <span className="text-teal-400">{item.provider_used || "Desconocido"}</span>
                  </span>
                </div>
              </div>
              <div className="ml-4 shrink-0">
                <span className="flex items-center gap-1 text-teal-400 font-medium text-sm">
                  Ver Detalles
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
                 className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-50 hover:bg-white/10 transition-colors"
               >
                 Anterior
               </button>
               <span className="px-4 py-2 text-gray-400">
                 Página {page} de {Math.ceil(data.total / data.page_size)}
               </span>
               <button 
                 onClick={() => setPage(p => Math.min(Math.ceil(data.total / data.page_size), p + 1))}
                 disabled={page >= Math.ceil(data.total / data.page_size)}
                 className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-50 hover:bg-white/10 transition-colors"
               >
                 Siguiente
               </button>
             </div>
          )}
        </div>
      )}
    </div>
  );
}
