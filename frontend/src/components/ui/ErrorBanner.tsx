"use client";

interface ErrorBannerProps {
  readonly error: string;
  readonly action?: { label: string; onClick: () => void };
  readonly centered?: boolean;
}

export function ErrorBanner({ error, action, centered = false }: ErrorBannerProps) {
  return (
    <div
      className={`text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 p-4 rounded-xl border border-red-200 dark:border-red-500/20 transition-colors ${
        centered ? "text-center p-6 rounded-2xl" : ""
      }`}
    >
      <p className={action ? "mb-4" : ""}>{error}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-gray-100 dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/20 rounded-lg transition-colors text-gray-900 dark:text-white text-sm font-medium"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
