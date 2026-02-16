import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names with Tailwind conflict resolution.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string for display.
 */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Fecha desconocida";
  return new Intl.DateTimeFormat("es-ES", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateStr));
}

/**
 * Get a color class for a bias score (0-1).
 */
export function getBiasColor(score: number | null): string {
  if (score === null) return "text-gray-400";
  if (score < 0.2) return "text-emerald-500";
  if (score < 0.4) return "text-lime-500";
  if (score < 0.6) return "text-amber-500";
  if (score < 0.8) return "text-orange-500";
  return "text-red-500";
}

/**
 * Get a human-readable label for a bias score.
 */
export function getBiasLabel(score: number | null): string {
  if (score === null) return "Sin datos";
  if (score < 0.2) return "Muy neutral";
  if (score < 0.4) return "Mayormente neutral";
  if (score < 0.6) return "Sesgo moderado";
  if (score < 0.8) return "Sesgo alto";
  return "Sesgo extremo";
}

/**
 * Truncate text to a max length.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "…";
}
