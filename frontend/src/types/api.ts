/** Tipos espelhando os schemas Pydantic do backend (app/schemas). */

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  checks: Record<string, string>;
}

export interface Profile {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface ProfileUpdate {
  full_name?: string;
  avatar_url?: string | null;
}

// ---------------------------------------------------------------- documentos
export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  title: string;
  original_filename: string;
  file_size: number;
  page_count: number | null;
  processed_pages: number;
  status: DocumentStatus;
  error_message: string | null;
  folder_id: string | null;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  progress: number;
}

export interface DocumentPage {
  document_id: string;
  page_number: number;
  page_count: number;
  text: string;
}

// ---------------------------------------------------------------- conversas
export interface Citation {
  id: string;
  rank: number;
  document_id: string;
  document_title: string;
  page_number: number;
  excerpt: string;
  score: number | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations: Citation[];
}

export interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

/** Eventos do endpoint SSE POST /conversations/{id}/messages. */
export type ChatStreamEvent =
  | { type: "status"; stage: "retrieving" | "generating"; sources?: number }
  | { type: "token"; delta: string }
  | { type: "done"; message: ChatMessage; abstained: boolean; grounded: boolean }
  | { type: "error"; code: string; message: string };

// ---------------------------------------------------------------- pastas
export interface Folder {
  id: string;
  name: string;
  color: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------- estatísticas
export interface DocumentStats {
  total: number;
  ready: number;
  processing: number;
  failed: number;
}

export interface UsagePoint {
  day: string;
  prompt_tokens: number;
  completion_tokens: number;
  events: number;
}

export interface StatsOverview {
  documents: DocumentStats;
  pages_indexed: number;
  chunks: number;
  conversations: number;
  questions: number;
  analyses: number;
  prompt_tokens: number;
  completion_tokens: number;
  usage_by_kind: Record<string, number>;
  daily_usage: UsagePoint[];
}

// ---------------------------------------------------------------- análises
export type AnalysisType = "summary" | "key_info" | "comparison";

export interface Analysis {
  id: string;
  type: AnalysisType;
  document_ids: string[];
  document_titles: string[];
  title: string;
  content: string;
  model: string | null;
  created_at: string;
}

export interface AnalysisListItem {
  id: string;
  type: AnalysisType;
  document_ids: string[];
  document_titles: string[];
  title: string;
  created_at: string;
}

// ---------------------------------------------------------------- busca
export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number;
  excerpt: string;
  similarity: number;
  score: number;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResultItem[];
}
