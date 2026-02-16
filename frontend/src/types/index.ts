/**
 * TypeScript type definitions for the News Neutralizer domain.
 */

// ── Core Types ────────────────────────────────────────────────

export interface ArticlePreview {
  title: string;
  source_name: string;
  source_url: string;
  author: string | null;
  published_at: string | null;
  topics: string[];
}

export interface Article {
  id: number;
  title: string;
  source_name: string;
  source_url: string;
  author: string | null;
  published_at: string | null;
  body: string;
  bias_score: number | null;
  bias_details: BiasDetails | null;
  cluster_id: number | null;
  is_source: boolean;
}

export interface BiasDetails {
  [key: string]: unknown;
}

export interface BiasElement {
  source: string;
  type: "sensacionalismo" | "omisión" | "framing" | "adjetivación" | "falacia";
  original_text: string;
  explanation: string;
  severity: number; // 1-5
}

export interface SourceBiasScore {
  score: number; // 0.0-1.0
  direction: "izquierda" | "centro" | "derecha" | "sensacionalista";
  confidence: number; // 0.0-1.0
}

export interface AnalysisResult {
  topic_summary: string;
  objective_facts: string[];
  bias_elements: BiasElement[];
  neutralized_summary: string;
  source_bias_scores: Record<string, SourceBiasScore>;
  provider_used: string;
  tokens_used: number | null;
}

// ── Task Types ────────────────────────────────────────────────

export type TaskStatus =
  | "pending"
  | "scraping"
  | "analyzing"
  | "completed"
  | "failed"
  | "preview";

export interface SearchTask {
  task_id: string;
  status: TaskStatus;
  progress: number;
  query: string | null;
  source_url: string | null;
  source_article?: {
    title: string;
    source_name: string;
    source_url: string;
  };
  created_at: string;
  completed_at?: string | null;
  articles: Article[];
  analysis?: AnalysisResult | null;
  error_message?: string | null;
}

export interface TaskCreated {
  task_id: string;
  message: string;
}

// ── Settings Types ────────────────────────────────────────────

export type AIProvider = "openai" | "anthropic" | "google" | "ollama";

export interface APIKeyInfo {
  provider: AIProvider;
  is_valid: boolean;
  created_at: string;
}

// ── Source Types ───────────────────────────────────────────────

export interface AvailableSource {
  name: string;
  slug: string;
  country: string;
  type: "rss" | "web";
  enabled: boolean;
}
