"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Article } from "@/types"; // Alias it inside if needed, or replace ArticleOut with Article

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export default function GeneratedNewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const newsId = params.newsId as string;

  const [news, setNews] = useState<GeneratedNewsDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!newsId) return;

    const fetchDetail = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/api/v1/generate/${newsId}`);
        if (!res.ok) {
            if (res.status === 404) throw new Error("Noticia generada no encontrada.");
            throw new Error("Error al cargar la noticia generada.");
        }
        
        const data = await res.json();
        setNews(data);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [newsId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6 animate-pulse">
        <div className="h-4 w-24 bg-white/10 rounded mb-8"></div>
        <div className="h-10 w-3/4 bg-white/10 rounded-lg mb-4"></div>
        <div className="h-6 w-full bg-white/10 rounded mb-8"></div>
        <div className="space-y-3">
          <div className="h-4 bg-white/10 rounded w-full"></div>
          <div className="h-4 bg-white/10 rounded w-full"></div>
          <div className="h-4 bg-white/10 rounded w-5/6"></div>
          <div className="h-4 bg-white/10 rounded w-full"></div>
        </div>
      </div>
    );
  }

  if (error || !news) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6">
        <div className="text-red-400 bg-red-500/10 p-6 rounded-2xl border border-red-500/20 text-center">
          <p className="mb-4">{error || "No se pudo cargar la información."}</p>
          <button 
            onClick={() => router.push("/generated")}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-white text-sm font-medium"
          >
            Volver a Noticias Generadas
          </button>
        </div>
      </div>
    );
  }

  // Format the body to highlight citations like [1], [2]
  const formatBody = (text: string) => {
      // Split by newline to render paragraphs
      const paragraphs = text.split('\n').filter(p => p.trim() !== '');
      
      return paragraphs.map((paragraph, index) => {
          // A rudimentary way to highlight bracket citations. 
          // React replaces the match with a span.
          const parts = paragraph.split(/(\[\d+\])/g);
          
          return (
              <p key={index} className="mb-4 text-gray-300 leading-relaxed text-lg">
                  {parts.map((part, i) => {
                      if (part.match(/\[\d+\]/)) {
                          return (
                              <span key={i} className="inline-flex items-center justify-center bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono text-xs font-bold rounded px-1.5 mx-0.5 cursor-help" title="Referencia a hecho extraído">
                                  {part}
                              </span>
                          );
                      }
                      return part;
                  })}
              </p>
          );
      });
  };

  // Group facts by their type or just display them
  const facts = news.traces.map(t => t.structured_fact).filter(f => f.type === "FACT");

  return (
    <div className="max-w-4xl mx-auto py-10 px-6">
      <Link href="/generated" className="inline-flex items-center text-sm text-gray-400 hover:text-white transition-colors mb-8 group">
        <svg className="w-4 h-4 mr-2 transform group-hover:-translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Volver a Noticias Generadas
      </Link>

      <article className="bg-gray-900 border border-white/5 rounded-3xl p-8 sm:p-12 shadow-2xl relative overflow-hidden">
        {/* Top Decorative gradient */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500" />

        <header className="mb-10">
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <span className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
              Noticia Consolidada Autogenerada
            </span>
            <span className="text-sm text-gray-500 font-medium">
              {new Date(news.created_at).toLocaleDateString("es-ES", { year: 'numeric', month: 'long', day: 'numeric' })}
            </span>
          </div>

          <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-white leading-tight mb-6">
            {news.title}
          </h1>

          <p className="text-xl sm:text-2xl text-gray-400 font-display leading-relaxed border-l-4 border-purple-500/50 pl-4 sm:pl-6">
            {news.lead}
          </p>
        </header>

        {/* Metrics Row */}
        <div className="flex flex-wrap gap-4 py-6 border-y border-white/5 mb-10 bg-white/[0.01] -mx-8 px-8 sm:-mx-12 sm:px-12">
            {news.reliability_score_achieved !== null && (
                <div className="flex flex-col">
                    <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Consenso Factual</span>
                    <span className="text-2xl font-display font-bold text-purple-400">
                        {Math.round(news.reliability_score_achieved)}%
                    </span>
                </div>
            )}
            <div className="w-px h-12 bg-white/10 hidden sm:block mx-4" />
            <div className="flex flex-col">
                <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Fuentes Analizadas</span>
                <span className="text-2xl font-display font-bold text-white">
                    {news.context_articles_ids.length}
                </span>
            </div>
            <div className="w-px h-12 bg-white/10 hidden sm:block mx-4" />
            <div className="flex flex-col">
                <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Hechos Nucleares</span>
                <span className="text-2xl font-display font-bold text-white">
                    {facts.length}
                </span>
            </div>
        </div>

        {/* Main Body */}
        <div className="prose prose-invert prose-lg max-w-none prose-p:text-gray-300">
          {formatBody(news.body)}
        </div>
      </article>

      {/* Traceability Section */}
      <section className="mt-12 space-y-8">
        <div>
            <h3 className="text-2xl font-display font-bold text-white mb-6 flex items-center gap-3">
                <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                Trazabilidad Numérica
            </h3>
            
            <div className="bg-gray-900 border border-white/5 rounded-2xl p-6">
                <p className="text-sm text-gray-400 mb-6">Esta noticia ha sido redactada estructurando exclusivamente los siguientes hechos, verificados transversalmente por el motor de IA.</p>
                <div className="grid gap-4">
                    {facts.map((fact, idx) => (
                        <div key={fact.id} className="flex gap-4 items-start p-4 bg-white/[0.02] rounded-xl border border-white/5">
                            <span className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-purple-500/20 text-purple-400 font-mono text-sm font-bold">
                                {idx + 1}
                            </span>
                            <div className="flex-1">
                                <p className="text-gray-200 text-sm leading-relaxed">{fact.content}</p>
                                <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                                    <span className="font-medium text-gray-400">Origen interno:</span> Artículo ID #{fact.article_id}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>

        {/* Sources Section */}
        <div>
            <h3 className="text-2xl font-display font-bold text-white mb-6 flex items-center gap-3">
                <svg className="w-6 h-6 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                Fuentes Originales Contrastadas
            </h3>

            <div className="grid sm:grid-cols-2 gap-4">
                {news.source_articles.map((article) => (
                    <a 
                        key={article.id}
                        href={article.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group flex flex-col p-5 bg-gray-900 border border-white/5 rounded-2xl hover:bg-white/[0.02] hover:border-teal-500/30 transition-all"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-teal-500/10 text-teal-400 border border-teal-500/20">
                                {article.source_name}
                            </span>
                            {article.bias_score !== null && (
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${article.bias_score > 0.6 ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-green-500/10 text-green-400 border-green-500/20'}`}>
                                    Sesgo: {Math.round(article.bias_score * 100)}%
                                </span>
                            )}
                        </div>
                        <h4 className="text-gray-200 font-bold group-hover:text-teal-400 transition-colors line-clamp-2 leading-snug mb-2">
                            {article.title}
                        </h4>
                        <div className="mt-auto pt-4 flex items-center justify-between text-xs text-gray-500 border-t border-white/5">
                            <span>{new Date(article.published_at || article.analyzed_at || '').toLocaleDateString()}</span>
                            <span className="flex items-center gap-1 group-hover:text-teal-400 transition-colors">
                                Leer Original
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
