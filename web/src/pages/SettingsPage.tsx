import { ArrowLeft, ImagePlus, Settings, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clampOpacity, loadUserPreferences, saveUserPreferences, type UserPreferences } from "@/lib/userPreferences";
import { cn } from "@/lib/utils";

const settingsItems = [{ id: "config", label: "配置", icon: Settings }];

export function SettingsPage() {
  const [activeItem, setActiveItem] = useState("config");
  const [preferences, setPreferences] = useState<UserPreferences>(() => loadUserPreferences());
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    saveUserPreferences(preferences);
  }, [preferences]);

  function updatePreference(nextPreference: Partial<UserPreferences>) {
    setPreferences((current) => ({ ...current, ...nextPreference }));
  }

  function onBackgroundUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      updatePreference({ chatBackgroundImage: typeof reader.result === "string" ? reader.result : "" });
    };
    reader.readAsDataURL(file);
    event.target.value = "";
  }

  function removeBackground() {
    updatePreference({ chatBackgroundImage: "" });
  }

  return (
    <div className="grid min-h-[calc(100dvh-7rem)] overflow-hidden rounded-lg border bg-surface shadow-sm lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="border-b bg-muted/30 lg:border-b-0 lg:border-r">
        <div className="border-b p-3">
          <Button asChild variant="ghost" className="w-full justify-start">
            <Link to="/chat">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              返回
            </Link>
          </Button>
        </div>
        <nav className="space-y-1 p-3" aria-label="设置项">
          {settingsItems.map((item) => {
            const Icon = item.icon;
            const active = activeItem === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={cn(
                  "flex min-h-11 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-background hover:text-foreground"
                )}
                onClick={() => setActiveItem(item.id)}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="min-h-0 overflow-y-auto p-4 app-scrollbar sm:p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          <header>
            <h1 className="text-2xl font-semibold">设置</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">调整对话页的 RAG 显示和个性化背景。</p>
          </header>

          {activeItem === "config" ? (
            <div className="space-y-5">
              <section className="rounded-lg border bg-background p-4">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-base font-semibold">显示参考段落</h2>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">RAG 模式回答后是否展示命中的知识库参考段落。</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={preferences.showRagReferences}
                    className={cn(
                      "relative h-7 w-12 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      preferences.showRagReferences ? "bg-primary" : "bg-muted-foreground/30"
                    )}
                    onClick={() => updatePreference({ showRagReferences: !preferences.showRagReferences })}
                  >
                    <span
                      className={cn(
                        "absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-transform",
                        preferences.showRagReferences ? "translate-x-6" : "translate-x-1"
                      )}
                    />
                    <span className="sr-only">切换 RAG 参考段落显示</span>
                  </button>
                </div>
              </section>

              <section className="rounded-lg border bg-background p-4">
                <div className="flex flex-col gap-5 lg:grid lg:grid-cols-[minmax(0,1fr)_280px]">
                  <div className="space-y-5">
                    <div>
                      <h2 className="text-base font-semibold">聊天背景</h2>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">上传图片后会应用到对话页面，可调整显示透明度。</p>
                    </div>

                    <div className="space-y-2">
                      <Label>背景图片</Label>
                      <input
                        ref={fileInputRef}
                        className="hidden"
                        type="file"
                        accept="image/*"
                        aria-hidden="true"
                        tabIndex={-1}
                        onChange={onBackgroundUpload}
                      />
                      <div className="flex flex-wrap gap-3">
                        <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                          <ImagePlus className="h-4 w-4" aria-hidden="true" />
                          上传图片
                        </Button>
                        <Button type="button" variant="ghost" disabled={!preferences.chatBackgroundImage} onClick={removeBackground}>
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                          删除背景
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <Label htmlFor="background-opacity">背景透明度</Label>
                        <span className="text-sm tabular-nums text-muted-foreground">{Math.round(preferences.chatBackgroundOpacity * 100)}%</span>
                      </div>
                      <Input
                        id="background-opacity"
                        type="range"
                        min="5"
                        max="100"
                        step="5"
                        value={Math.round(preferences.chatBackgroundOpacity * 100)}
                        onChange={(event) => updatePreference({ chatBackgroundOpacity: clampOpacity(Number(event.target.value) / 100) })}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border bg-surface p-3">
                    <p className="text-sm font-medium">预览</p>
                    <div className="relative mt-3 aspect-[4/3] overflow-hidden rounded-md border bg-background">
                      {preferences.chatBackgroundImage ? (
                        <img
                          src={preferences.chatBackgroundImage}
                          alt="聊天背景预览"
                          className="absolute inset-0 h-full w-full object-cover"
                          style={{ opacity: preferences.chatBackgroundOpacity }}
                        />
                      ) : null}
                      <div className="absolute inset-0 bg-background/45" />
                      <div className="relative z-10 flex h-full flex-col justify-end gap-3 p-4">
                        <div className="max-w-[80%] rounded-lg border bg-surface px-3 py-2 text-sm shadow-sm">知识库中有哪些重点？</div>
                        <div className="ml-auto max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground shadow-sm">请用 RAG 模式回答。</div>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
