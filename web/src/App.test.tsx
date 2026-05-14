import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { App } from "@/App";

const now = "2026-05-14T00:00:00Z";
let mockSettings = {
  show_rag_references: true,
  chat_background_image: "",
  chat_background_opacity: 0.2,
  updated_at: now
};
let mockSessions: unknown[] = [];
let writeTextMock: ReturnType<typeof vi.fn>;

const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  if (url.endsWith("/chat/sessions")) {
    return new Response(JSON.stringify({ sessions: mockSessions }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (url.includes("/chat/sessions/")) {
    const sessionId = url.split("/chat/sessions/")[1];
    const session = mockSessions.find((item) => typeof item === "object" && item !== null && "id" in item && item.id === sessionId);
    return new Response(JSON.stringify(session ?? { id: sessionId, title: "会话", messages: [], created_at: now, updated_at: now }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  }
  if (url.endsWith("/settings")) {
    if (String(init?.method ?? "GET").toUpperCase() === "PUT") {
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      mockSettings = { ...mockSettings, ...body, updated_at: now };
    }
    return new Response(JSON.stringify(mockSettings), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  if (url.endsWith("/documents")) {
    return new Response(JSON.stringify({ files: [], total_files: 0, total_chunks: 0 }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  }
  if (url.endsWith("/agent/chat")) {
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
    const message = String(body.message ?? "测试 markdown");
    const isRag = message.includes("RAG");
    return new Response(
      JSON.stringify({
        answer: isRag ? "RAG 回答" : "## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```",
        question: message,
        prompt: "agent prompt",
        used_rag: isRag,
        references: isRag ? [{ index: 1, page_content: "参考内容", metadata: {}, score: 0.12 }] : [],
        model: "test",
        usage: {},
        session: {
          id: isRag ? "rag-session" : "chat-session",
          title: isRag ? "测试 RAG" : "测试 markdown",
          created_at: now,
          updated_at: now,
          messages: [
            { id: isRag ? "u-rag" : "u-chat", role: "user", content: message, mode: isRag ? "rag" : "normal", references: [], created_at: now },
            {
              id: isRag ? "a-rag" : "a-chat",
              role: "assistant",
              content: isRag ? "RAG 回答" : "## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```",
              mode: isRag ? "rag" : "normal",
              references: isRag ? [{ index: 1, page_content: "参考内容", metadata: {}, score: 0.12 }] : [],
              created_at: now
            }
          ]
        }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }
  if (url.endsWith("/rag/chat")) {
    return new Response(
      JSON.stringify({
        answer: "RAG 回答",
        question: "测试 RAG",
        prompt: "prompt",
        references: [{ index: 1, page_content: "参考内容", metadata: {}, score: 0.12 }],
        model: "test",
        usage: {},
        session: {
          id: "rag-session",
          title: "测试 RAG",
          created_at: now,
          updated_at: now,
          messages: [
            { id: "u-rag", role: "user", content: "测试 RAG", mode: "rag", references: [], created_at: now },
            {
              id: "a-rag",
              role: "assistant",
              content: "RAG 回答",
              mode: "rag",
              references: [{ index: 1, page_content: "参考内容", metadata: {}, score: 0.12 }],
              created_at: now
            }
          ]
        }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }
  if (url.endsWith("/chat")) {
    return new Response(
      JSON.stringify({
        answer: "## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```",
        model: "test",
        usage: {},
        session: {
          id: "chat-session",
          title: "测试 markdown",
          created_at: now,
          updated_at: now,
          messages: [
            { id: "u-chat", role: "user", content: "测试 markdown", mode: "normal", references: [], created_at: now },
            { id: "a-chat", role: "assistant", content: "## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```", mode: "normal", references: [], created_at: now }
          ]
        }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }
  return new Response(JSON.stringify({ status: "ok" }), { status: 200, headers: { "Content-Type": "application/json" } });
});

vi.stubGlobal("fetch", fetchMock);

function renderApp(initialEntry = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    mockSettings = {
      show_rag_references: true,
      chat_background_image: "",
      chat_background_opacity: 0.2,
      updated_at: now
    };
    mockSessions = [];
    writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      configurable: true
    });
    fetchMock.mockClear();
  });

  it("renders status page by default", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "系统控制台" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "知识库概览" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent 对话动态" })).toBeInTheDocument();
  });

  it("renders user chat route", () => {
    renderApp("/chat");
    expect(screen.getByRole("heading", { name: "新会话" })).toBeInTheDocument();
    expect(screen.getByText("开始一次知识库对话")).toBeInTheDocument();
  });

  it("renders markdown answer in chat route", async () => {
    renderApp("/chat");
    await userEvent.type(screen.getByRole("textbox", { name: "输入消息" }), "测试 markdown");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));

    expect(await screen.findByRole("heading", { name: "回答标题" })).toBeInTheDocument();
    expect(screen.getByText("第一条")).toBeInTheDocument();
    expect(screen.getByText("print('ok')")).toBeInTheDocument();
  });

  it("copies user question and assistant answer in chat route", async () => {
    renderApp("/chat");
    await userEvent.type(screen.getByRole("textbox", { name: "输入消息" }), "复制测试");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));
    await screen.findByRole("heading", { name: "回答标题" });

    const copyButtons = screen.getAllByRole("button", { name: "复制消息" });
    await userEvent.click(copyButtons[0]);
    expect(writeTextMock).toHaveBeenCalledWith("复制测试");

    await userEvent.click(copyButtons[1]);
    expect(writeTextMock).toHaveBeenLastCalledWith("## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```");
  });

  it("does not persist session when creating a new chat only", async () => {
    renderApp("/chat");
    await userEvent.click(screen.getByRole("button", { name: "新增会话" }));

    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("shows session after a successful completed chat", async () => {
    renderApp("/chat");
    await userEvent.type(screen.getByRole("textbox", { name: "输入消息" }), "测试保存");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));
    await screen.findByRole("heading", { name: "回答标题" });

    expect(screen.getAllByText("测试 markdown").length).toBeGreaterThan(0);
  });

  it("sorts chat sessions by updated time descending", async () => {
    mockSessions = [
      { id: "old", title: "旧会话", created_at: "2026-05-13T09:00:00Z", updated_at: "2026-05-13T09:00:00Z", messages: [] },
      { id: "new", title: "新会话", created_at: "2026-05-14T09:00:00Z", updated_at: "2026-05-14T09:00:00Z", messages: [] },
      { id: "middle", title: "中间会话", created_at: "2026-05-13T18:00:00Z", updated_at: "2026-05-13T18:00:00Z", messages: [] }
    ];

    renderApp("/chat");

    await screen.findByText("旧会话");
    const titles = Array.from(document.querySelectorAll("aside button .text-sm.font-medium")).map((element) => element.textContent);
    expect(titles).toEqual(["新会话", "中间会话", "旧会话"]);
  });

  it("renders settings page from shell entry", async () => {
    renderApp("/knowledge");
    await userEvent.click(screen.getAllByRole("link", { name: "设置" })[0]);

    expect(screen.getByRole("heading", { name: "设置" })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "切换 RAG 参考段落显示" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("button", { name: "个性化" }));
    expect(screen.getByRole("button", { name: "上传图片" })).toBeInTheDocument();
  });

  it("uses settings to hide rag references in chat route", async () => {
    mockSettings.show_rag_references = false;
    renderApp("/chat");
    await userEvent.type(screen.getByRole("textbox", { name: "输入消息" }), "测试 RAG");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));

    expect(await screen.findAllByText("RAG 回答")).toHaveLength(2);
    expect(screen.queryByText("参考段落 1")).not.toBeInTheDocument();
  });

  it("applies updated settings after returning to chat without reload", async () => {
    mockSettings.show_rag_references = false;
    renderApp("/settings");

    const switchButton = await screen.findByRole("switch", { name: "切换 RAG 参考段落显示" });
    await waitFor(() => expect(switchButton).toHaveAttribute("aria-checked", "false"));
    await userEvent.click(switchButton);
    expect(await screen.findByRole("switch", { name: "切换 RAG 参考段落显示" })).toHaveAttribute("aria-checked", "true");

    await userEvent.click(screen.getByRole("link", { name: "返回" }));
    await userEvent.type(screen.getByRole("textbox", { name: "输入消息" }), "测试 RAG");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));

    expect(await screen.findByText("参考段落 1")).toBeInTheDocument();
  });
});
