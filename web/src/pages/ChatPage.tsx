import { useMutation } from "@tanstack/react-query";
import { MessageSquarePlus, Search, Send, Trash2, Bot, User, Sparkles, Loader2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { chatWithModel, chatWithRag } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatHistoryMessage, RagReference } from "@/types/api";

type ChatMode = "normal" | "rag";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: ChatMode;
  references?: RagReference[];
  createdAt: string;
};

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

const STORAGE_KEY = "rag-starter.chat.sessions";

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions());
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0]?.id ?? "");
  const [conversationSearch, setConversationSearch] = useState("");
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("normal");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null,
    [sessions, activeSessionId]
  );
  const filteredSessions = useMemo(() => {
    const keyword = conversationSearch.trim().toLowerCase();
    if (!keyword) {
      return sessions;
    }
    return sessions.filter((session) => {
      const haystack = [session.title, ...session.messages.map((message) => message.content)].join(" ").toLowerCase();
      return haystack.includes(keyword);
    });
  }, [sessions, conversationSearch]);

  const chatMutation = useMutation({
    mutationFn: async ({ message, history, activeMode }: { message: string; history: ChatHistoryMessage[]; activeMode: ChatMode }) => {
      if (activeMode === "rag") {
        return {
          activeMode,
          response: await chatWithRag({
            question: message,
            k: 2,
            history
          })
        };
      }
      return {
        activeMode,
        response: await chatWithModel({
          message,
          history
        })
      };
    },
    onSuccess: ({ response, activeMode }) => {
      appendAssistantMessage(response.answer, activeMode, "references" in response ? response.references : undefined);
    },
    onError: (error) => {
      appendAssistantMessage(error instanceof Error ? error.message : "请求失败，请稍后重试。", mode);
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (!activeSessionId && sessions[0]) {
      setActiveSessionId(sessions[0].id);
    }
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (typeof messageEndRef.current?.scrollIntoView === "function") {
      messageEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [activeSession?.messages.length, chatMutation.isPending]);

  function createSession() {
    const now = new Date().toISOString();
    const session: ChatSession = {
      id: crypto.randomUUID(),
      title: "新会话",
      messages: [],
      createdAt: now,
      updatedAt: now
    };
    setSessions((current) => [session, ...current]);
    setActiveSessionId(session.id);
    setInput("");
  }

  function deleteSession(sessionId: string) {
    const confirmed = window.confirm("确认删除这个会话？");
    if (!confirmed) {
      return;
    }
    setSessions((current) => {
      const next = current.filter((session) => session.id !== sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(next[0]?.id ?? "");
      }
      return next;
    });
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || chatMutation.isPending) {
      return;
    }

    const session = activeSession ?? createEmptySession();
    const history = toHistory(session.messages);
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      mode,
      createdAt: new Date().toISOString()
    };
    upsertSessionWithMessage(session, userMessage);
    setInput("");
    chatMutation.mutate({ message, history, activeMode: mode });
  }

  function appendAssistantMessage(content: string, activeMode: ChatMode, references?: RagReference[]) {
    const session = activeSession ?? createEmptySession();
    const assistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content,
      mode: activeMode,
      references,
      createdAt: new Date().toISOString()
    };
    upsertSessionWithMessage(session, assistantMessage);
  }

  function upsertSessionWithMessage(session: ChatSession, message: ChatMessage) {
    const now = new Date().toISOString();
    setSessions((current) => {
      const exists = current.some((item) => item.id === session.id);
      const nextSession: ChatSession = {
        ...session,
        title: session.title === "新会话" && message.role === "user" ? titleFromMessage(message.content) : session.title,
        messages: [...session.messages, message],
        updatedAt: now
      };
      if (!exists) {
        setActiveSessionId(nextSession.id);
        return [nextSession, ...current];
      }
      return [nextSession, ...current.filter((item) => item.id !== session.id)];
    });
  }

  function createEmptySession() {
    const now = new Date().toISOString();
    const session: ChatSession = {
      id: crypto.randomUUID(),
      title: "新会话",
      messages: [],
      createdAt: now,
      updatedAt: now
    };
    setActiveSessionId(session.id);
    return session;
  }

  return (
    <div className="grid min-h-[calc(100dvh-7rem)] overflow-hidden rounded-lg border bg-surface shadow-sm xl:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="border-b bg-muted/30 xl:border-b-0 xl:border-r">
        <div className="space-y-3 border-b p-4">
          <Button className="w-full justify-start" onClick={createSession}>
            <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            新增会话
          </Button>
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              className="pl-9"
              value={conversationSearch}
              onChange={(event) => setConversationSearch(event.target.value)}
              placeholder="搜索会话"
            />
          </label>
        </div>
        <div className="max-h-[34dvh] overflow-y-auto p-2 app-scrollbar xl:max-h-[calc(100dvh-15rem)]">
          {filteredSessions.length ? (
            filteredSessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  "group flex items-center gap-2 rounded-md p-2",
                  activeSession?.id === session.id ? "bg-primary/10" : "hover:bg-background"
                )}
              >
                <button className="min-h-11 min-w-0 flex-1 text-left" type="button" onClick={() => setActiveSessionId(session.id)}>
                  <span className="block truncate text-sm font-medium">{session.title}</span>
                  <span className="mt-1 block truncate text-xs text-muted-foreground">{session.messages.at(-1)?.content || "暂无消息"}</span>
                </button>
                <Button variant="ghost" size="icon" aria-label={`删除 ${session.title}`} onClick={() => deleteSession(session.id)}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            ))
          ) : (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">没有匹配会话</p>
          )}
        </div>
      </aside>

      <section className="flex min-h-[calc(100dvh-7rem)] flex-col">
        <header className="flex items-center justify-between gap-3 border-b px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold">{activeSession?.title ?? "新会话"}</h1>
            <p className="mt-1 text-sm text-muted-foreground">支持普通模型对话和 RAG 检索增强对话</p>
          </div>
          <Badge variant={mode === "rag" ? "default" : "outline"}>{mode === "rag" ? "RAG" : "LLM"}</Badge>
        </header>

        <div className="flex-1 overflow-y-auto bg-background px-4 py-6 app-scrollbar">
          <div className="mx-auto max-w-3xl space-y-5">
            {activeSession?.messages.length ? (
              activeSession.messages.map((message) => <MessageBubble key={message.id} message={message} />)
            ) : (
              <div className="flex min-h-[42dvh] flex-col items-center justify-center text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Sparkles className="h-6 w-6" aria-hidden="true" />
                </div>
                <h2 className="mt-4 text-xl font-semibold">开始一次知识库对话</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                  直接提问使用普通模型回答；开启 RAG 后，会先检索本地知识库，再生成增强回答。
                </p>
              </div>
            )}
            {chatMutation.isPending ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                正在生成回答
              </div>
            ) : null}
            <div ref={messageEndRef} />
          </div>
        </div>

        <form className="border-t bg-surface p-4" onSubmit={onSubmit}>
          <div className="mx-auto max-w-3xl rounded-lg border bg-background p-3 shadow-sm">
            <Textarea
              className="min-h-20 border-0 bg-transparent shadow-none focus-visible:ring-0"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={mode === "rag" ? "向知识库提问..." : "输入消息..."}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="inline-flex rounded-md border bg-surface p-1">
                <button
                  type="button"
                  className={cn("rounded px-3 py-1.5 text-sm font-medium", mode === "normal" ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
                  onClick={() => setMode("normal")}
                >
                  LLM
                </button>
                <button
                  type="button"
                  className={cn("rounded px-3 py-1.5 text-sm font-medium", mode === "rag" ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
                  onClick={() => setMode("rag")}
                >
                  RAG
                </button>
              </div>
              <Button type="submit" size="icon" disabled={!input.trim() || chatMutation.isPending} aria-label="发送消息">
                {chatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
              </Button>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <article className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      ) : null}
      <div className={cn("max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6", isUser ? "bg-primary text-primary-foreground" : "border bg-surface")}>
        <div className="whitespace-pre-wrap">{message.content}</div>
        {message.mode === "rag" && !isUser ? <Badge className="mt-3" variant="outline">RAG</Badge> : null}
        {message.references?.length ? (
          <div className="mt-3 space-y-2 border-t pt-3">
            {message.references.map((reference) => (
              <details key={reference.index} className="text-xs text-muted-foreground">
                <summary className="cursor-pointer font-medium">参考段落 {reference.index}</summary>
                <p className="mt-1 whitespace-pre-wrap">{reference.page_content}</p>
              </details>
            ))}
          </div>
        ) : null}
      </div>
      {isUser ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <User className="h-4 w-4" aria-hidden="true" />
        </div>
      ) : null}
    </article>
  );
}

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as ChatSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toHistory(messages: ChatMessage[]): ChatHistoryMessage[] {
  return messages.slice(-12).map((message) => ({
    role: message.role,
    content: message.content
  }));
}

function titleFromMessage(message: string) {
  return message.length > 24 ? `${message.slice(0, 24)}...` : message;
}
