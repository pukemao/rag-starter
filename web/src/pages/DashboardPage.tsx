import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ServerCrash } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { API_BASE_URL, getHealth } from "@/lib/api";

export function DashboardPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 15000,
    retry: 1
  });

  const isHealthy = health.data?.status === "ok";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">知识库工作台</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          管理本地知识库索引、相似度检索和 RAG 增强对话，前端直接连接当前 FastAPI 服务。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Panel>
          <PanelHeader>
            <PanelTitle>服务状态</PanelTitle>
            <PanelDescription>自动轮询 `/health`</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <div className="flex items-center gap-3">
              {isHealthy ? (
                <CheckCircle2 className="h-8 w-8 text-emerald-600" aria-hidden="true" />
              ) : (
                <ServerCrash className="h-8 w-8 text-destructive" aria-hidden="true" />
              )}
              <div>
                <Badge variant={isHealthy ? "success" : "warning"}>{isHealthy ? "online" : "unavailable"}</Badge>
                <p className="mt-2 text-sm text-muted-foreground">{health.isFetching ? "正在检查..." : "最近一次检查已完成"}</p>
              </div>
            </div>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>后端地址</PanelTitle>
            <PanelDescription>可通过 `VITE_API_BASE_URL` 覆盖</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <p className="break-all rounded-md bg-muted p-3 text-sm leading-6">{API_BASE_URL}</p>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>默认链路</PanelTitle>
            <PanelDescription>索引、检索、生成</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>分割器：recursive</p>
              <p>向量库：Chroma</p>
              <p>LLM：DeepSeek via LangChain</p>
            </div>
          </PanelContent>
        </Panel>
      </div>

      <Panel>
        <PanelHeader>
          <PanelTitle>工作流</PanelTitle>
          <PanelDescription>按顺序完成一次知识库问答</PanelDescription>
        </PanelHeader>
        <PanelContent>
          <div className="grid gap-3 md:grid-cols-4">
            {["上传文件并索引", "输入问题检索", "查看引用段落", "生成 RAG 回答"].map((item, index) => (
              <div key={item} className="rounded-lg border bg-background p-4">
                <Badge variant="outline">Step {index + 1}</Badge>
                <p className="mt-3 text-sm font-medium">{item}</p>
              </div>
            ))}
          </div>
        </PanelContent>
      </Panel>
    </div>
  );
}
