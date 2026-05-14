import { useMutation } from "@tanstack/react-query";
import { MessageSquarePlus, Search, Send, Trash2, Bot, User, Sparkles, Loader2, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";

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

type MarkdownBlock =
  | { type: "heading"; level: 1 | 2 | 3; content: string }
  | { type: "paragraph"; content: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "quote"; content: string }
  | { type: "code"; language: string; content: string };

const STORAGE_KEY = "rag-starter.chat.sessions";

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions());
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0]?.id ?? "");
  const [conversationSearch, setConversationSearch] = useState("");
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("normal");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

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

  useEffect(() => {
    resizeInput();
  }, [input]);

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

  function onInputChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setInput(event.target.value);
  }

  function resizeInput() {
    const textarea = inputRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "0px";
    const lineHeight = 24;
    const maxRows = 6;
    const maxHeight = lineHeight * maxRows;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${Math.max(lineHeight, nextHeight)}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
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
    <div
      className={cn(
        "grid h-[calc(100dvh-10px)] overflow-hidden rounded-lg border bg-surface shadow-sm",
        sidebarOpen ? "xl:grid-cols-[300px_minmax(0,1fr)]" : "xl:grid-cols-[minmax(0,1fr)]"
      )}
    >
      <aside className={cn("min-h-0 border-b bg-muted/30 xl:border-b-0 xl:border-r", !sidebarOpen && "hidden")}>
        <div className="space-y-3 border-b p-3">
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
        <div className="h-[calc(100%-8.5rem)] overflow-y-auto p-2 app-scrollbar">
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

      <section className="flex min-h-0 flex-col">
        <header className="flex min-h-[56px] items-center justify-between gap-3 border-b px-4 py-2">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              type="button"
              aria-label={sidebarOpen ? "隐藏会话侧边栏" : "显示会话侧边栏"}
              onClick={() => setSidebarOpen((open) => !open)}
            >
              {sidebarOpen ? <PanelLeftClose className="h-4 w-4" aria-hidden="true" /> : <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />}
            </Button>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold">{activeSession?.title ?? "新会话"}</h1>
              <p className="mt-1 truncate text-sm text-muted-foreground">支持普通模型对话和 RAG 检索增强对话</p>
            </div>
          </div>
          <Badge variant={mode === "rag" ? "default" : "outline"}>{mode === "rag" ? "RAG" : "LLM"}</Badge>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto bg-background px-4 py-5 app-scrollbar">
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

        <form className="border-t bg-surface p-3" onSubmit={onSubmit}>
          <div className="mx-auto max-w-3xl rounded-lg border bg-background p-2 shadow-sm">
            <Textarea
              ref={inputRef}
              rows={1}
              className="max-h-36 min-h-6 resize-none border-0 bg-transparent px-2 py-1.5 leading-6 shadow-none focus-visible:ring-0 app-scrollbar"
              value={input}
              onChange={onInputChange}
              placeholder={mode === "rag" ? "向知识库提问..." : "输入消息..."}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="mt-2 flex items-center justify-between gap-3">
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
        {isUser ? <div className="whitespace-pre-wrap">{message.content}</div> : <MarkdownContent content={message.content} />}
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

function MarkdownContent({ content }: { content: string }) {
  const blocks = useMemo(() => parseMarkdown(content), [content]);

  return (
    <div className="space-y-3 break-words text-sm leading-6">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const HeadingTag = block.level === 1 ? "h2" : block.level === 2 ? "h3" : "h4";
          return (
            <HeadingTag key={index} className="font-semibold leading-7 text-foreground">
              {renderInlineMarkdown(block.content)}
            </HeadingTag>
          );
        }
        if (block.type === "ul") {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "ol") {
          return (
            <ol key={index} className="list-decimal space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
              ))}
            </ol>
          );
        }
        if (block.type === "quote") {
          return (
            <blockquote key={index} className="border-l-2 border-primary/40 pl-3 text-muted-foreground">
              {renderInlineMarkdown(block.content)}
            </blockquote>
          );
        }
        if (block.type === "code") {
          return (
            <pre key={index} className="overflow-x-auto rounded-md bg-muted p-3 text-xs leading-5 app-scrollbar">
              <code>{block.content}</code>
            </pre>
          );
        }
        return (
          <p key={index} className="whitespace-pre-wrap">
            {renderInlineMarkdown(block.content)}
          </p>
        );
      })}
    </div>
  );
}

function parseMarkdown(content: string): MarkdownBlock[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let paragraph: string[] = [];
  let codeLines: string[] | null = null;
  let codeLanguage = "";
  let listType: "ul" | "ol" | null = null;
  let listItems: string[] = [];

  function flushParagraph() {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", content: paragraph.join("\n").trim() });
      paragraph = [];
    }
  }

  function flushList() {
    if (listType && listItems.length) {
      blocks.push({ type: listType, items: listItems });
      listType = null;
      listItems = [];
    }
  }

  for (const line of lines) {
    const fence = line.match(/^```(\w+)?\s*$/);
    if (fence) {
      if (codeLines) {
        blocks.push({ type: "code", language: codeLanguage, content: codeLines.join("\n") });
        codeLines = null;
        codeLanguage = "";
      } else {
        flushParagraph();
        flushList();
        codeLines = [];
        codeLanguage = fence[1] ?? "";
      }
      continue;
    }

    if (codeLines) {
      codeLines.push(line);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", level: heading[1].length as 1 | 2 | 3, content: heading[2].trim() });
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    if (unordered) {
      flushParagraph();
      if (listType !== "ul") {
        flushList();
        listType = "ul";
      }
      listItems.push(unordered[1].trim());
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      if (listType !== "ol") {
        flushList();
        listType = "ol";
      }
      listItems.push(ordered[1].trim());
      continue;
    }

    const quote = line.match(/^>\s?(.+)$/);
    if (quote) {
      flushParagraph();
      flushList();
      blocks.push({ type: "quote", content: quote[1].trim() });
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  if (codeLines) {
    blocks.push({ type: "code", language: codeLanguage, content: codeLines.join("\n") });
  }
  flushParagraph();
  flushList();

  return blocks.length ? blocks : [{ type: "paragraph", content }];
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text))) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("`")) {
      nodes.push(
        <code key={`${match.index}-code`} className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
          {token.slice(1, -1)}
        </code>
      );
    } else {
      nodes.push(
        <strong key={`${match.index}-strong`} className="font-semibold">
          {token.slice(2, -2)}
        </strong>
      );
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
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
