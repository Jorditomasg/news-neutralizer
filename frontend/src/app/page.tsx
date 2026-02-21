"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const isUrl = query.trim().match(/^https?:\/\//);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <div className="flex flex-col items-center pt-20 pb-16">
      {/* Hero */}
      <div className="mb-12 text-center">
        <h1 className="font-display text-5xl font-bold tracking-tight sm:text-6xl">
          Descubre los{" "}
          <span className="bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
            hechos
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-gray-400">
          Compara noticias de múltiples fuentes, detecta sesgo informativo y
          obtén un resumen neutral basado en hechos verificables.
        </p>
      </div>

      {/* Unified Search Form */}
      <form
        onSubmit={handleSearch}
        className="w-full max-w-2xl"
      >
        <div className="group relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe un tema o pega la URL de una noticia..."
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-lg text-white placeholder-gray-500 outline-none transition-all focus:border-teal-400/40 focus:bg-white/[0.07] focus:ring-2 focus:ring-teal-400/20"
          />
          
          {/* Input Type Indicator Badge */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            
            <button
              type="submit"
              disabled={!query.trim()}
              className="rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 px-5 py-2 text-sm font-semibold text-gray-950 transition-all hover:shadow-lg hover:shadow-teal-500/25 disabled:opacity-40 ml-2"
            >
              {isUrl ? "Analizar URL" : "Buscar"}
            </button>
          </div>
        </div>
      </form>
      
      <div className="mt-8">
      </div>

      {/* Feature Cards */}
      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
          <div className="mb-3 text-2xl">📊</div>
          <h3 className="font-display text-sm font-semibold text-white">
            Comparación multi-fuente
          </h3>
          <p className="mt-2 text-sm text-gray-500">
            Analiza cómo diferentes medios cubren la misma noticia, detectando omisiones y énfasis.
          </p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
          <div className="mb-3 text-2xl">🎯</div>
          <h3 className="font-display text-sm font-semibold text-white">
            Detección de sesgo
          </h3>
          <p className="mt-2 text-sm text-gray-500">
            Identifica sensacionalismo, framing, adjetivación y otros elementos de polarización.
          </p>
        </div>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
          <div className="mb-3 text-2xl">✍️</div>
          <h3 className="font-display text-sm font-semibold text-white">
            Resumen neutral
          </h3>
          <p className="mt-2 text-sm text-gray-500">
            Genera un resumen basado exclusivamente en hechos verificables, sin opinión editorial.
          </p>
        </div>
      </div>
    </div>
  );
}
