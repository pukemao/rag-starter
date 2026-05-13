import type {
  ApiErrorPayload,
  DeleteDocumentResponse,
  HealthResponse,
  IndexResponse,
  RagChatResponse,
  SearchResponse
} from "@/types/api";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function parseError(response: Response) {
  let payload: ApiErrorPayload | undefined;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }

  const detail = payload?.detail;
  if (typeof detail === "string") {
    return new ApiError(detail, response.status, payload);
  }
  if (detail?.message) {
    return new ApiError(detail.message, response.status, payload);
  }
  return new ApiError(`请求失败，状态码 ${response.status}`, response.status, payload);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    }
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as T;
}

export function getHealth() {
  return requestJson<HealthResponse>("/health");
}

export type IndexFilesInput = {
  files: File[];
  splitterType: string;
  chunkSize: number;
  chunkOverlap: number;
};

export function indexFiles(input: IndexFilesInput) {
  const formData = new FormData();
  input.files.forEach((file) => formData.append("files", file));
  formData.append("splitter_type", input.splitterType);
  formData.append("chunk_size", String(input.chunkSize));
  formData.append("chunk_overlap", String(input.chunkOverlap));

  return requestJson<IndexResponse>("/index", {
    method: "POST",
    body: formData
  });
}

export function searchKnowledgeBase(input: { query: string; k: number; filter?: Record<string, unknown> | null }) {
  return requestJson<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function chatWithRag(input: {
  question: string;
  k: number;
  filter?: Record<string, unknown> | null;
  temperature?: number | null;
  max_tokens?: number | null;
}) {
  return requestJson<RagChatResponse>("/rag/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function deleteDocuments(input: { ids?: string[] | null; source?: string | null }) {
  return requestJson<DeleteDocumentResponse>("/documents", {
    method: "DELETE",
    body: JSON.stringify(input)
  });
}
