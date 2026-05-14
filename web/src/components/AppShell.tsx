import { Activity, Database, FileStack, FileUp, MessageSquareText, Search, Settings, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { cn } from "@/lib/utils";

const navigation = [
  { to: "/knowledge", label: "知识库", icon: FileStack },
  { to: "/status", label: "状态", icon: Activity },
  { to: "/index", label: "索引", icon: FileUp },
  { to: "/search", label: "检索", icon: Search },
  { to: "/chat", label: "对话", icon: MessageSquareText },
  { to: "/rag-chat", label: "RAG 调试", icon: MessageSquareText },
  { to: "/delete", label: "删除", icon: Trash2 }
];

const mobileNavigation = [...navigation, { to: "/settings", label: "设置", icon: Settings }];

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const isChatRoute = location.pathname === "/chat";
  const isFullBleedRoute = isChatRoute || location.pathname === "/settings";

  return (
    <div className="min-h-dvh bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r bg-surface lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Database className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold">RAG Starter</p>
                <p className="text-xs text-muted-foreground">Knowledge Console</p>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4" aria-label="主导航">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/knowledge"}
                  className={({ isActive }) =>
                    cn(
                      "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      isActive && "bg-primary/10 text-primary"
                    )
                  }
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
          <div className="border-t px-3 py-4">
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                cn(
                  "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive && "bg-primary/10 text-primary"
                )
              }
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              设置
            </NavLink>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b bg-surface/95 backdrop-blur">
          <div className="flex min-h-16 flex-col gap-3 px-4 py-3 sm:px-6 lg:hidden">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Database className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold">RAG Starter</p>
                <p className="text-xs text-muted-foreground">Knowledge Console</p>
              </div>
            </div>
            <nav className="flex gap-2 overflow-x-auto pb-1 app-scrollbar" aria-label="移动端导航">
              {mobileNavigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/knowledge"}
                    className={({ isActive }) =>
                      cn(
                        "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md border px-3 text-sm font-medium text-muted-foreground",
                        isActive && "border-primary bg-primary/10 text-primary"
                      )
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </header>
        <main className={cn("mx-auto w-full", isFullBleedRoute ? "max-w-none p-[5px]" : "max-w-7xl px-4 py-6 sm:px-6 lg:px-8")}>{children}</main>
      </div>
    </div>
  );
}
