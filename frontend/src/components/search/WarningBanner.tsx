"use client";

interface WarningBannerProps {
  readonly warnings: string[];
  readonly title?: string;
}

export function WarningBanner({ warnings, title = "Contenido posiblemente incompleto" }: WarningBannerProps) {
  if (warnings.length === 0) return null;

  return (
    <div className="mb-6 space-y-2 animate-fade-in">
      {warnings.map((warning, i) => (
        <div
          key={`warning-${i}-${warning.slice(0, 20)}`}
          className="rounded-2xl border border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-5 backdrop-blur-sm"
        >
          <div className="flex gap-3 items-start">
            <div className="shrink-0 mt-0.5 h-8 w-8 rounded-full bg-amber-100 dark:bg-amber-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-amber-800 dark:text-amber-400 text-sm mb-1">{title}</h3>
              <p className="text-amber-700/90 dark:text-amber-300/80 text-sm leading-relaxed">{warning}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
