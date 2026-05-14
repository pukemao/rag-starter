import { useMutation, useQuery } from "@tanstack/react-query";
import { MessageSquarePlus, Search, Send, Trash2, Bot, User, Sparkles, Loader2, PanelLeftClose, PanelLeftOpen, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { chatWithAgent, deleteChatSession, getChatSession, getUserSettings, listChatSessions } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatHistoryMessage, ChatSessionResponse, RagReference, UserSettingsResponse } from "@/types/api";

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

function createDraftSession(): ChatSession {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "新会话",
    messages: [],
    createdAt: now,
    updatedAt: now
  };
}

function toChatSession(session: ChatSessionResponse): ChatSession {
  return {
    id: session.id,
    title: session.title,
    messages: session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      mode: message.mode ?? undefined,
      references: message.references,
      createdAt: message.created_at
    })),
    createdAt: session.created_at,
    updatedAt: session.updated_at
  };
}

function toUserPreferences(settings: UserSettingsResponse) {
  return {
    showRagReferences: settings.show_rag_references,
    chatBackgroundImage: settings.chat_background_image,
    chatBackgroundOpacity: settings.chat_background_opacity
  };
}

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [conversationSearch, setConversationSearch] = useState("");
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [draftSession, setDraftSession] = useState<ChatSession | null>(null);
  const [pendingMessages, setPendingMessages] = useState<ChatMessage[]>([]);
  const [transientError, setTransientError] = useState("");
  const [preferences, setPreferences] = useState(() => ({ showRagReferences: true, chatBackgroundImage: "", chatBackgroundOpacity: 0.2 }));
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const storedActiveSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null,
    [sessions, activeSessionId]
  );
  const activeSession = draftSession ?? storedActiveSession;
  const visibleMessages = [...(activeSession?.messages ?? []), ...pendingMessages];
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

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: listChatSessions,
    staleTime: 30_000
  });

  const settingsQuery = useQuery({
    queryKey: ["user-settings"],
    queryFn: getUserSettings,
    refetchOnMount: "always",
    refetchOnWindowFocus: true
  });

  const chatMutation = useMutation({
    mutationFn: async ({
      message,
      history,
      sessionId
    }: {
      message: string;
      history: ChatHistoryMessage[];
      sessionId: string | null;
      session: ChatSession;
      userMessage: ChatMessage;
    }) => {
      return {
        response: await chatWithAgent({
          session_id: sessionId,
          message,
          k: 2,
          history
        })
      };
    },
    onSuccess: ({ response }, variables) => {
      const nextSession = response.session ? toChatSession(response.session) : completeLocalSession(variables.session, variables.userMessage, response.answer, response.used_rag ? "rag" : "normal", response.references);
      persistReturnedSession(nextSession);
    },
    onError: (error) => {
      setPendingMessages([]);
      setTransientError(error instanceof Error ? error.message : "请求失败，请稍后重试。");
    }
  });

  useEffect(() => {
    if (sessionsQuery.data) {
      setSessions((current) =>
        sessionsQuery.data.sessions.map((session) => {
          const next = toChatSession(session);
          const existing = current.find((item) => item.id === next.id);
          return existing?.messages.length ? { ...next, messages: existing.messages } : next;
        })
      );
    }
  }, [sessionsQuery.data]);

  useEffect(() => {
    if (settingsQuery.data) {
      setPreferences(toUserPreferences(settingsQuery.data));
    }
  }, [settingsQuery.data]);

  useEffect(() => {
    if (!activeSessionId && !draftSession && sessions[0]) {
      void activateSession(sessions[0].id);
    }
  }, [activeSessionId, draftSession, sessions]);

  useEffect(() => {
    if (typeof messageEndRef.current?.scrollIntoView === "function") {
      messageEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [visibleMessages.length, transientError, chatMutation.isPending]);

  useEffect(() => {
    resizeInput();
  }, [input]);

  function createSession() {
    setDraftSession(createDraftSession());
    setActiveSessionId("");
    setPendingMessages([]);
    setTransientError("");
    setInput("");
  }

  function deleteSession(sessionId: string) {
    const confirmed = window.confirm("确认删除这个会话？");
    if (!confirmed) {
      return;
    }
    void deleteChatSession(sessionId).catch((error) => {
      setTransientError(error instanceof Error ? error.message : "删除会话失败");
    });
    setSessions((current) => {
      const next = current.filter((session) => session.id !== sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(next[0]?.id ?? "");
      }
      return next;
    });
  }

  async function activateSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setDraftSession(null);
    setPendingMessages([]);
    setTransientError("");
    try {
      const session = toChatSession(await getChatSession(sessionId));
      persistReturnedSession(session);
    } catch (error) {
      setTransientError(error instanceof Error ? error.message : "加载会话失败");
    }
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
      createdAt: new Date().toISOString()
    };
    setDraftSession(session);
    setPendingMessages([userMessage]);
    setTransientError("");
    setInput("");
    chatMutation.mutate({ message, history, session, userMessage, sessionId: activeSessionId || null });
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

  function completeLocalSession(session: ChatSession, userMessage: ChatMessage, content: string, activeMode: ChatMode, references?: RagReference[]) {
    const assistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content,
      mode: activeMode,
      references,
      createdAt: new Date().toISOString()
    };
    const now = new Date().toISOString();
    return {
      ...session,
      title: session.title === "新会话" ? titleFromMessage(userMessage.content) : session.title,
      messages: [...session.messages, userMessage, assistantMessage],
      updatedAt: now
    };
  }

  function persistReturnedSession(nextSession: ChatSession) {
    setActiveSessionId(nextSession.id);
    setDraftSession(null);
    setPendingMessages([]);
    setTransientError("");
    setSessions((current) => {
      const exists = current.some((item) => item.id === nextSession.id);
      const withoutCurrent = current.filter((item) => item.id !== nextSession.id);
      return exists ? [nextSession, ...withoutCurrent] : [nextSession, ...current];
    });
  }

  function createEmptySession() {
    const session = createDraftSession();
    setDraftSession(session);
    setActiveSessionId("");
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
                <button className="min-h-11 min-w-0 flex-1 text-left" type="button" onClick={() => activateSession(session.id)}>
                  <span className="block truncate text-sm font-medium">{session.title}</span>
                  <span className="mt-1 block truncate text-xs text-muted-foreground">{session.messages.at(-1)?.content || "点击查看会话"}</span>
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
              <p className="mt-1 truncate text-sm text-muted-foreground">智能判断是否需要检索本地知识库</p>
            </div>
          </div>
          <Badge variant="outline">Agent</Badge>
        </header>

        <div className="relative min-h-0 flex-1 overflow-hidden bg-background">
          {preferences.chatBackgroundImage ? (
            <img
              src={preferences.chatBackgroundImage}
              alt=""
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 h-full w-full object-cover"
              style={{ opacity: preferences.chatBackgroundOpacity }}
            />
          ) : null}
          <div className="relative z-10 h-full overflow-y-auto px-4 pb-36 pt-5 app-scrollbar">
            <div className="mx-auto max-w-3xl space-y-5">
              {visibleMessages.length ? (
                visibleMessages.map((message) => <MessageBubble key={message.id} message={message} showRagReferences={preferences.showRagReferences} />)
              ) : (
                <div className="flex min-h-[42dvh] flex-col items-center justify-center text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Sparkles className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <h2 className="mt-4 text-xl font-semibold">开始一次知识库对话</h2>
                  <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                    直接提问即可，系统会根据问题自动判断是否需要检索本地知识库。
                  </p>
                </div>
              )}
              {chatMutation.isPending ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  正在生成回答
                </div>
              ) : null}
              {transientError ? <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{transientError}</p> : null}
              <div ref={messageEndRef} />
            </div>
          </div>
        </div>

        <form className="relative z-20 bg-gradient-to-t from-surface via-surface/95 to-surface/0 px-4 pb-5 pt-3" onSubmit={onSubmit}>
          <div className="mx-auto flex max-w-4xl items-center gap-3 rounded-[2rem] border bg-surface/95 px-4 py-3 shadow-[0_18px_45px_hsl(var(--foreground)/0.16)] backdrop-blur">
            <Button type="button" variant="ghost" size="icon" className="h-10 w-10 shrink-0 rounded-full" aria-label="添加内容">
              <Plus className="h-5 w-5" aria-hidden="true" />
            </Button>
            <Textarea
              ref={inputRef}
              rows={1}
              aria-label="输入消息"
              className="max-h-36 min-h-10 flex-1 resize-none border-0 bg-transparent px-0 py-2 text-base leading-6 shadow-none focus-visible:ring-0 app-scrollbar"
              value={input}
              onChange={onInputChange}
              placeholder="有问题，尽管问"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="flex shrink-0 items-center gap-2">
              <Button type="submit" size="icon" className="h-12 w-12 rounded-full" disabled={!input.trim() || chatMutation.isPending} aria-label="发送消息">
                {chatMutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Send className="h-5 w-5" aria-hidden="true" />}
              </Button>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}

function MessageBubble({ message, showRagReferences }: { message: ChatMessage; showRagReferences: boolean }) {
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
        {showRagReferences && message.references?.length ? (
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

function toHistory(messages: ChatMessage[]): ChatHistoryMessage[] {
  return messages.slice(-12).map((message) => ({
    role: message.role,
    content: message.content
  }));
}

function titleFromMessage(message: string) {
  return message.length > 24 ? `${message.slice(0, 24)}...` : message;
}
