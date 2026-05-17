import type {
  AgentChatResponse,
  ApiErrorPayload,
  ChatHistoryMessage,
  ChatFileResponse,
  ChatResponse,
  ChatSessionListResponse,
  ChatSessionResponse,
  DeleteDocumentResponse,
  HealthResponse,
  IndexResponse,
  ListDocumentsResponse,
  RagChatResponse,
  SearchResponse,
  UserSettingsResponse
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

export function listDocuments() {
  return requestJson<ListDocumentsResponse>("/documents");
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

export function chatWithModel(input: {
  session_id?: string | null;
  message: string;
  history?: ChatHistoryMessage[];
  temperature?: number | null;
  max_tokens?: number | null;
}) {
  return requestJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function chatWithRag(input: {
  session_id?: string | null;
  question: string;
  k: number;
  filter?: Record<string, unknown> | null;
  history?: ChatHistoryMessage[];
  temperature?: number | null;
  max_tokens?: number | null;
}) {
  return requestJson<RagChatResponse>("/rag/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function chatWithAgent(input: {
  session_id?: string | null;
  message: string;
  k?: number;
  history?: ChatHistoryMessage[];
  file_ids?: string[];
}) {
  return requestJson<AgentChatResponse>("/agent/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export type AgentChatStreamEvent =
  | { event: "start"; data: Record<string, never> }
  | { event: "delta"; data: { content: string } }
  | { event: "done"; data: AgentChatResponse }
  | { event: "error"; data: { message: string } };

export async function chatWithAgentStream(
  input: {
    session_id?: string | null;
    message: string;
    k?: number;
    history?: ChatHistoryMessage[];
    file_ids?: string[];
  },
  onEvent: (event: AgentChatStreamEvent) => void
) {
  const response = await fetch(`${API_BASE_URL}/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  if (!response.body) {
    throw new ApiError("当前浏览器不支持流式响应", response.status, null);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }
      onEvent(JSON.parse(trimmed) as AgentChatStreamEvent);
    }
  }

  buffer += decoder.decode();
  const tail = buffer.trim();
  if (tail) {
    onEvent(JSON.parse(tail) as AgentChatStreamEvent);
  }
}

export function uploadChatFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<ChatFileResponse>("/chat/files", {
    method: "POST",
    body: formData
  });
}

export function deleteDocuments(input: { ids?: string[] | null; source?: string | null; source_id?: string | null }) {
  return requestJson<DeleteDocumentResponse>("/documents", {
    method: "DELETE",
    body: JSON.stringify(input)
  });
}

export function listChatSessions() {
  return requestJson<ChatSessionListResponse>("/chat/sessions");
}

export function getChatSession(sessionId: string) {
  return requestJson<ChatSessionResponse>(`/chat/sessions/${sessionId}`);
}

export function deleteChatSession(sessionId: string) {
  return requestJson<{ deleted: boolean }>(`/chat/sessions/${sessionId}`, {
    method: "DELETE"
  });
}

export function getUserSettings() {
  return requestJson<UserSettingsResponse>("/settings");
}

export function updateUserSettings(input: Partial<Pick<UserSettingsResponse, "show_rag_references" | "chat_background_image" | "chat_background_opacity">>) {
  return requestJson<UserSettingsResponse>("/settings", {
    method: "PUT",
    body: JSON.stringify(input)
  });
}
