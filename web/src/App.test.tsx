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
});
