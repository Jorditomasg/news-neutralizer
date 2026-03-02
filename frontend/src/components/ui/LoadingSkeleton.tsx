"use client";

interface LoadingSkeletonProps {
  readonly variant?: "list" | "detail";
  readonly count?: number;
}

export function LoadingSkeleton({ variant = "list", count = 3 }: LoadingSkeletonProps) {
  if (variant === "detail") {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6 animate-pulse">
        <div className="h-4 w-24 bg-gray-200 dark:bg-white/10 rounded mb-8 transition-colors" />
        <div className="h-10 w-3/4 bg-gray-200 dark:bg-white/10 rounded-lg mb-4 transition-colors" />
        <div className="h-6 w-full bg-gray-200 dark:bg-white/10 rounded mb-8 transition-colors" />
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 dark:bg-white/10 rounded w-full transition-colors" />
          <div className="h-4 bg-gray-200 dark:bg-white/10 rounded w-full transition-colors" />
          <div className="h-4 bg-gray-200 dark:bg-white/10 rounded w-5/6 transition-colors" />
          <div className="h-4 bg-gray-200 dark:bg-white/10 rounded w-full transition-colors" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Array.from({ length: count }, (_, i) => (
        <div
          key={`skeleton-${i}`}
          className="h-24 bg-gray-100 dark:bg-white/5 animate-pulse rounded-xl border border-gray-200 dark:border-white/5 transition-colors"
        />
      ))}
    </div>
  );
}
