import { useState, KeyboardEvent } from "react";

interface SearchFormProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [query, setQuery] = useState("");
  const isUrl = (text: string) => text.startsWith("http://") || text.startsWith("https://") || !!text.match(/^www\./);
  const isUrlDetected = isUrl(query);

  const handleSubmit = () => {
    if (query.trim()) {
      onSearch(query);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-2xl flex flex-col items-center gap-4">
      {/* Input Field */}
      <div className="w-full relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-teal-500 via-cyan-500 to-teal-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
        <div className="relative flex items-center bg-white dark:bg-white/5 backdrop-blur-xl border border-gray-200 dark:border-white/10 rounded-2xl p-2 shadow-2xl ring-1 ring-gray-100 dark:ring-white/5 transition-colors">
          <div className="pl-4 text-gray-500 dark:text-gray-400">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un tema o pega un enlace..."
            className="w-full bg-transparent border-none text-gray-900 dark:text-white text-lg placeholder-gray-400 dark:placeholder-gray-500 focus:ring-0 px-4 py-3"
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Action Button */}
      <div className="flex w-full justify-center">
        <button
          onClick={handleSubmit}
          disabled={isLoading || !query.trim()}
          className={`px-8 py-3 rounded-xl font-bold text-white shadow-lg transition-all transform hover:scale-105 active:scale-95 flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
            isUrlDetected
              ? "bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 shadow-blue-500/25"
              : "bg-gradient-to-r from-teal-500 to-cyan-600 hover:from-teal-400 hover:to-cyan-500 shadow-teal-500/25"
          }`}
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Analizando...</span>
            </>
          ) : (
            <>
              <span>{isUrlDetected ? "🔗" : "🔍"}</span>
              <span>{isUrlDetected ? "Analizar Enlace" : "Analizar Tema"}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
