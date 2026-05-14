import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  FileStack,
  Gauge,
  MessageSquareText,
  RefreshCw,
  ServerCrash,
  Settings,
  ShieldCheck,
  Sparkles,
  TriangleAlert
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { API_BASE_URL, getHealth, getUserSettings, listChatSessions, listDocuments } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatSessionResponse, KnowledgeFile } from "@/types/api";

type ExtensionMetric = {
  extension: string;
  files: number;
  chunks: number;
};

type ActivityMetric = {
  label: string;
  count: number;
};

const CHECK_ITEMS = [
  { label: "服务健康检查", description: "FastAPI /health 自动轮询", icon: Activity },
  { label: "知识库持久化", description: "Chroma 本地向量库", icon: Database },
  { label: "Agent 工具调用", description: "自动判断是否检索知识库", icon: Bot },
  { label: "设置持久化", description: "SQLite 保存用户配置", icon: Settings }
];

export function DashboardPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 15000,
    retry: 1
  });
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 20000,
    retry: 1
  });
  const sessions = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: listChatSessions,
    refetchInterval: 20000,
    retry: 1
  });
  const settings = useQuery({
    queryKey: ["user-settings"],
    queryFn: getUserSettings,
    refetchInterval: 30000,
    retry: 1
  });

  const isHealthy = health.data?.status === "ok";
  const files = documents.data?.files ?? [];
  const totalFiles = documents.data?.total_files ?? 0;
  const totalChunks = documents.data?.total_chunks ?? 0;
  const sessionItems = sessions.data?.sessions ?? [];
  const latestSession = sessionItems[0] ?? null;
  const extensionMetrics = buildExtensionMetrics(files);
  const activityMetrics = buildActivityMetrics(sessionItems);
  const averageChunks = totalFiles ? Math.round(totalChunks / totalFiles) : 0;
  const ragReferenceVisible = settings.data?.show_rag_references ?? true;
  const hasBackground = Boolean(settings.data?.chat_background_image);
  const isBusy = health.isFetching || documents.isFetching || sessions.isFetching || settings.isFetching;
  const hasError = health.isError || documents.isError || sessions.isError || settings.isError;

  function refreshAll() {
    void health.refetch();
    void documents.refetch();
    void sessions.refetch();
    void settings.refetch();
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={isHealthy ? "success" : "warning"}>{isHealthy ? "系统在线" : "服务异常"}</Badge>
            <span className="text-xs text-muted-foreground">自动刷新 15-30 秒</span>
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal">系统控制台</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            集中查看知识库规模、Agent 对话状态、系统配置和服务可用性。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={refreshAll} disabled={isBusy}>
            <RefreshCw className={cn("h-4 w-4", isBusy && "animate-spin")} aria-hidden="true" />
            刷新数据
          </Button>
          <Button asChild>
            <Link to="/knowledge">
              <FileStack className="h-4 w-4" aria-hidden="true" />
              管理知识库
            </Link>
          </Button>
        </div>
      </header>

      {hasError ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          部分控制台数据暂时不可用，请检查后端服务或稍后刷新。
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="核心指标">
        <MetricCard
          title="服务状态"
          value={isHealthy ? "Online" : "Offline"}
          description={`${health.isFetching ? "正在检查" : "最近检查完成"} · ${API_BASE_URL}`}
          icon={isHealthy ? CheckCircle2 : ServerCrash}
          tone={isHealthy ? "success" : "danger"}
        />
        <MetricCard title="知识库文件" value={totalFiles.toLocaleString()} description={`${totalChunks.toLocaleString()} 个文本块已入库`} icon={FileStack} tone="primary" />
        <MetricCard title="平均块数" value={averageChunks.toLocaleString()} description="每个文件的平均 chunk 数量" icon={Gauge} tone="neutral" />
        <MetricCard title="会话数量" value={sessionItems.length.toLocaleString()} description={latestSession ? `最近：${latestSession.title}` : "暂无持久化会话"} icon={MessageSquareText} tone="accent" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        <Panel>
          <PanelHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <PanelTitle>知识库概览</PanelTitle>
              <PanelDescription>按文件类型聚合文件数量和 chunk 规模</PanelDescription>
            </div>
            <Badge variant="outline">{extensionMetrics.length ? `${extensionMetrics.length} 类格式` : "暂无数据"}</Badge>
          </PanelHeader>
          <PanelContent>
            {extensionMetrics.length ? (
              <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
                <DonutChart metrics={extensionMetrics} />
                <div className="space-y-3">
                  {extensionMetrics.map((metric) => (
                    <FormatBar key={metric.extension} metric={metric} maxChunks={Math.max(...extensionMetrics.map((item) => item.chunks))} />
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState title="知识库尚未索引文件" description="上传文档后，这里会展示文件类型分布和文本块规模。" actionLabel="上传文件" to="/knowledge" />
            )}
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>Agent 对话动态</PanelTitle>
            <PanelDescription>最近会话活跃度与上下文能力</PanelDescription>
          </PanelHeader>
          <PanelContent>
            {sessionItems.length ? (
              <div className="space-y-5">
                <MiniBarChart data={activityMetrics} />
                <div className="space-y-2">
                  {sessionItems.slice(0, 4).map((session) => (
                    <div key={session.id} className="flex items-center justify-between gap-3 rounded-md border bg-background px-3 py-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{session.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(session.updated_at)}</p>
                      </div>
                      <Badge variant="outline">{relativeAge(session.updated_at)}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState title="暂无对话记录" description="完成一次 Agent 对话后，这里会展示会话活跃度。" actionLabel="开始对话" to="/chat" />
            )}
          </PanelContent>
        </Panel>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel>
          <PanelHeader>
            <PanelTitle>系统链路</PanelTitle>
            <PanelDescription>当前 RAG 与 Agent 能力检查</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {CHECK_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="flex items-start gap-3 rounded-lg border bg-background p-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>用户配置</PanelTitle>
            <PanelDescription>对话体验相关设置</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <div className="space-y-3">
              <ConfigRow icon={ShieldCheck} label="RAG 参考段落" value={ragReferenceVisible ? "显示" : "隐藏"} active={ragReferenceVisible} />
              <ConfigRow icon={Sparkles} label="聊天背景" value={hasBackground ? "已配置" : "未配置"} active={hasBackground} />
              <ConfigRow icon={Clock3} label="设置更新时间" value={settings.data ? formatDateTime(settings.data.updated_at) : "等待同步"} active={Boolean(settings.data)} />
            </div>
          </PanelContent>
        </Panel>
      </section>
    </div>
  );
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  tone
}: {
  title: string;
  value: string;
  description: string;
  icon: typeof Activity;
  tone: "primary" | "success" | "danger" | "neutral" | "accent";
}) {
  const toneClass = {
    primary: "bg-primary/10 text-primary",
    success: "bg-emerald-50 text-emerald-700",
    danger: "bg-destructive/10 text-destructive",
    neutral: "bg-muted text-muted-foreground",
    accent: "bg-sky-50 text-sky-700"
  }[tone];
  return (
    <Panel>
      <PanelContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="mt-2 truncate text-2xl font-semibold tabular-nums">{value}</p>
          </div>
          <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-md", toneClass)}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        </div>
        <p className="mt-3 max-h-10 overflow-hidden text-xs leading-5 text-muted-foreground">{description}</p>
      </PanelContent>
    </Panel>
  );
}

function DonutChart({ metrics }: { metrics: ExtensionMetric[] }) {
  const total = metrics.reduce((sum, item) => sum + item.files, 0) || 1;
  const top = metrics[0];
  const circumference = 2 * Math.PI * 42;
  let offset = 0;

  return (
    <div className="flex items-center gap-5">
      <svg className="h-36 w-36 shrink-0 -rotate-90" viewBox="0 0 100 100" role="img" aria-label="知识库文件类型分布图">
        <circle cx="50" cy="50" r="42" fill="none" stroke="hsl(var(--muted))" strokeWidth="12" />
        {metrics.slice(0, 5).map((item, index) => {
          const length = (item.files / total) * circumference;
          const segment = (
            <circle
              key={item.extension}
              cx="50"
              cy="50"
              r="42"
              fill="none"
              stroke={chartColor(index)}
              strokeWidth="12"
              strokeDasharray={`${length} ${circumference - length}`}
              strokeDashoffset={-offset}
              strokeLinecap="round"
            />
          );
          offset += length;
          return segment;
        })}
      </svg>
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">主力格式</p>
        <p className="mt-1 text-2xl font-semibold">{top.extension}</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {top.files} 个文件，占知识库文件数 {Math.round((top.files / total) * 100)}%。
        </p>
      </div>
    </div>
  );
}

function FormatBar({ metric, maxChunks }: { metric: ExtensionMetric; maxChunks: number }) {
  const width = maxChunks ? Math.max(6, Math.round((metric.chunks / maxChunks) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{metric.extension}</span>
        <span className="tabular-nums text-muted-foreground">{metric.files} 文件 · {metric.chunks} chunks</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function MiniBarChart({ data }: { data: ActivityMetric[] }) {
  const max = Math.max(1, ...data.map((item) => item.count));
  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex h-32 items-end gap-2" aria-label="最近会话活跃度">
        {data.map((item) => (
          <div key={item.label} className="flex min-w-0 flex-1 flex-col items-center gap-2">
            <div className="flex h-24 w-full items-end rounded-md bg-muted">
              <div className="w-full rounded-md bg-primary/75 transition-[height] duration-300" style={{ height: `${Math.max(8, (item.count / max) * 100)}%` }} />
            </div>
            <span className="text-xs text-muted-foreground">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConfigRow({ icon: Icon, label, value, active }: { icon: typeof Activity; label: string; value: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border bg-background p-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-md", active ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground")}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <span className="truncate text-sm font-medium">{label}</span>
      </div>
      <Badge variant={active ? "default" : "outline"}>{value}</Badge>
    </div>
  );
}

function EmptyState({ title, description, actionLabel, to }: { title: string; description: string; actionLabel: string; to: string }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed bg-background p-6 text-center">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p>
      <Button asChild className="mt-4" variant="outline">
        <Link to={to}>{actionLabel}</Link>
      </Button>
    </div>
  );
}

function buildExtensionMetrics(files: KnowledgeFile[]): ExtensionMetric[] {
  const grouped = new Map<string, ExtensionMetric>();
  files.forEach((file) => {
    const extension = extensionOf(file.filename || file.source);
    const current = grouped.get(extension) ?? { extension, files: 0, chunks: 0 };
    current.files += 1;
    current.chunks += file.chunk_count;
    grouped.set(extension, current);
  });
  return [...grouped.values()].sort((left, right) => right.chunks - left.chunks || right.files - left.files).slice(0, 6);
}

function buildActivityMetrics(sessions: ChatSessionResponse[]): ActivityMetric[] {
  const buckets = ["今天", "7天", "30天", "更早"].map((label) => ({ label, count: 0 }));
  const now = Date.now();
  sessions.forEach((session) => {
    const ageDays = (now - new Date(session.updated_at).getTime()) / 86_400_000;
    if (ageDays <= 1) {
      buckets[0].count += 1;
    } else if (ageDays <= 7) {
      buckets[1].count += 1;
    } else if (ageDays <= 30) {
      buckets[2].count += 1;
    } else {
      buckets[3].count += 1;
    }
  });
  return buckets;
}

function extensionOf(filename: string) {
  const match = filename.toLowerCase().match(/\.([a-z0-9]+)$/);
  return match ? `.${match[1]}` : "unknown";
}

function chartColor(index: number) {
  return ["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626", "#0891b2"][index % 6];
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function relativeAge(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(diff / 60_000));
  if (minutes < 60) {
    return `${minutes || 1} 分钟内`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours} 小时前`;
  }
  return `${Math.round(hours / 24)} 天前`;
}
