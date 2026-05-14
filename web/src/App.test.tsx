import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { App } from "@/App";

const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input);
  if (url.endsWith("/documents")) {
    return new Response(JSON.stringify({ files: [], total_files: 0, total_chunks: 0 }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  }
  if (url.endsWith("/rag/chat")) {
    return new Response(
      JSON.stringify({
        answer: "RAG 回答",
        question: "测试 RAG",
        prompt: "prompt",
        references: [{ index: 1, page_content: "参考内容", metadata: {}, score: 0.12 }],
        model: "test",
        usage: {}
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }
  if (url.endsWith("/chat")) {
    return new Response(
      JSON.stringify({
        answer: "## 回答标题\n\n- 第一条\n- 第二条\n\n```python\nprint('ok')\n```",
        model: "test",
        usage: {}
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
    fetchMock.mockClear();
  });

  it("renders knowledge base page by default", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "知识库" })).toBeInTheDocument();
  });

  it("renders user chat route", () => {
    renderApp("/chat");
    expect(screen.getByRole("heading", { name: "新会话" })).toBeInTheDocument();
    expect(screen.getByText("开始一次知识库对话")).toBeInTheDocument();
  });

  it("renders markdown answer in chat route", async () => {
    renderApp("/chat");
    await userEvent.type(screen.getByPlaceholderText("输入消息..."), "测试 markdown");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));

    expect(await screen.findByRole("heading", { name: "回答标题" })).toBeInTheDocument();
    expect(screen.getByText("第一条")).toBeInTheDocument();
    expect(screen.getByText("print('ok')")).toBeInTheDocument();
  });

  it("renders settings page from shell entry", async () => {
    renderApp("/knowledge");
    await userEvent.click(screen.getAllByRole("link", { name: "设置" })[0]);

    expect(screen.getByRole("heading", { name: "设置" })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "切换 RAG 参考段落显示" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("button", { name: "上传图片" })).toBeInTheDocument();
  });

  it("uses settings to hide rag references in chat route", async () => {
    localStorage.setItem("rag-starter.user.preferences", JSON.stringify({ showRagReferences: false, chatBackgroundImage: "", chatBackgroundOpacity: 0.2 }));

    renderApp("/chat");
    await userEvent.click(screen.getByRole("button", { name: "RAG" }));
    await userEvent.type(screen.getByPlaceholderText("向知识库提问..."), "测试 RAG");
    await userEvent.click(screen.getByRole("button", { name: "发送消息" }));

    expect(await screen.findAllByText("RAG 回答")).toHaveLength(2);
    expect(screen.queryByText("参考段落 1")).not.toBeInTheDocument();
  });
});
