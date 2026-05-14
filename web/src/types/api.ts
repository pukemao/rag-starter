export type HealthResponse = {
  status: string;
};

export type IndexFileResponse = {
  filename: string;
  source_id: string;
  ids: string[];
  count: number;
  input_count: number;
  skipped_duplicates: number;
};

export type IndexResponse = {
  files: IndexFileResponse[];
  total_files: number;
  total_chunks: number;
  total_input_chunks: number;
  total_skipped_duplicates: number;
};

export type SearchResult = {
  page_content: string;
  metadata: Record<string, unknown>;
  score?: number | null;
};

export type SearchResponse = {
  results: SearchResult[];
};

export type ChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResponse = {
  answer: string;
  prompt: string;
  model: string;
  usage: Record<string, unknown>;
  session?: ChatSessionResponse | null;
};

export type RagReference = SearchResult & {
  index: number;
};

export type RagChatResponse = {
  answer: string;
  question: string;
  prompt: string;
  references: RagReference[];
  model: string;
  usage: Record<string, unknown>;
  session?: ChatSessionResponse | null;
};

export type AgentChatResponse = {
  answer: string;
  question: string;
  prompt: string;
  used_rag: boolean;
  references: RagReference[];
  attachments: GeneratedDocumentAttachment[];
  model: string;
  usage: Record<string, unknown>;
  session?: ChatSessionResponse | null;
};

export type GeneratedDocumentAttachment = {
  file_id: string;
  filename: string;
  document_type: "markdown" | "word" | "excel" | "pdf" | string;
  mime_type: string;
  download_url: string;
  size: number;
  created_at: string;
};

export type ChatMessageResponse = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: "normal" | "rag" | null;
  references: RagReference[];
  attachments: GeneratedDocumentAttachment[];
  created_at: string;
};

export type ChatSessionResponse = {
  id: string;
  title: string;
  messages: ChatMessageResponse[];
  created_at: string;
  updated_at: string;
};

export type ChatSessionListResponse = {
  sessions: ChatSessionResponse[];
};

export type UserSettingsResponse = {
  show_rag_references: boolean;
  chat_background_image: string;
  chat_background_opacity: number;
  updated_at: string;
};

export type DeleteDocumentResponse = {
  deleted?: number | null;
};

export type KnowledgeFile = {
  filename: string;
  source: string;
  source_id?: string | null;
  file_hash?: string | null;
  chunk_count: number;
  chunk_ids: string[];
};

export type ListDocumentsResponse = {
  files: KnowledgeFile[];
  total_files: number;
  total_chunks: number;
};

export type ApiErrorPayload = {
  detail?: string | { message?: string; filename?: string; file_hash?: string };
};
