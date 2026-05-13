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
