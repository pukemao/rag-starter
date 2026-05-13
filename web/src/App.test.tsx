import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { App } from "@/App";

vi.stubGlobal(
  "fetch",
  vi.fn(async () => new Response(JSON.stringify({ status: "ok" }), { status: 200, headers: { "Content-Type": "application/json" } }))
);

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
  it("renders dashboard", () => {
    renderApp();
    expect(screen.getByRole("heading", { name: "知识库工作台" })).toBeInTheDocument();
  });

  it("renders rag chat route", () => {
    renderApp("/chat");
    expect(screen.getByRole("heading", { name: "RAG 增强对话" })).toBeInTheDocument();
  });
});
