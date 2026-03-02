"use client";

interface PaginationProps {
  readonly page: number;
  readonly totalPages: number;
  readonly onPageChange: (page: number) => void;
  readonly labels: { prev: string; next: string; page: string };
}

export function Pagination({ page, totalPages, onPageChange, labels }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex justify-center gap-2 mt-8">
      <button
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page === 1}
        className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-white shadow-sm dark:shadow-none disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
      >
        {labels.prev}
      </button>
      <span className="px-4 py-2 text-gray-500 dark:text-gray-400">
        {labels.page
          .replace("{page}", page.toString())
          .replace("{total}", totalPages.toString())}
      </span>
      <button
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        className="px-4 py-2 rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-white shadow-sm dark:shadow-none disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
      >
        {labels.next}
      </button>
    </div>
  );
}
