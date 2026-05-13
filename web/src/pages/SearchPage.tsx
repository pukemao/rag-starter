import { useMutation } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import { useState, type FormEvent } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Field } from "@/components/Field";
import { ResultBlock } from "@/components/ResultBlock";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { Textarea } from "@/components/ui/textarea";
import { parseOptionalJson } from "@/lib/form";
import { searchKnowledgeBase } from "@/lib/api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(2);
  const [filter, setFilter] = useState("");
  const [formError, setFormError] = useState("");

  const mutation = useMutation({
    mutationFn: searchKnowledgeBase
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    try {
      mutation.mutate({ query, k, filter: parseOptionalJson(filter) });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "过滤条件格式错误");
    }
  }

  const results = mutation.data?.results ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">相似度检索</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          输入问题或关键词，返回向量数据库中最相似的知识库段落。
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        <Panel>
          <PanelHeader>
            <PanelTitle>检索条件</PanelTitle>
            <PanelDescription>filter 使用 Chroma metadata 查询对象</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <form className="space-y-5" onSubmit={onSubmit}>
              <Field label="问题" htmlFor="search-query">
                <Textarea id="search-query" value={query} onChange={(event) => setQuery(event.target.value)} required />
              </Field>
              <Field label="返回段落数 k" htmlFor="search-k">
                <Input id="search-k" type="number" min={1} value={k} onChange={(event) => setK(Number(event.target.value))} />
              </Field>
              <Field label="过滤条件" htmlFor="search-filter" description='例如 {"source":"report.pdf"}'>
                <Textarea
                  id="search-filter"
                  className="min-h-24 font-mono text-xs"
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                />
              </Field>

              {formError ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{formError}</p> : null}
              {mutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{mutation.error.message}</p> : null}

              <Button className="w-full" type="submit" disabled={!query.trim() || mutation.isPending}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Search className="h-4 w-4" aria-hidden="true" />}
                执行检索
              </Button>
            </form>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>匹配段落</PanelTitle>
            <PanelDescription>{mutation.data ? `返回 ${results.length} 段` : "等待检索请求"}</PanelDescription>
          </PanelHeader>
          <PanelContent>
            {!mutation.data ? (
              <EmptyState title="暂无检索结果" description="提交问题后，这里会展示相似段落、score 和 metadata。" />
            ) : results.length ? (
              <div className="space-y-4">
                {results.map((result, index) => (
                  <ResultBlock key={`${result.page_content}-${index}`} result={result} index={index + 1} />
                ))}
              </div>
            ) : (
              <EmptyState title="没有匹配段落" description="可以调大 k，或检查知识库是否已完成索引。" />
            )}
          </PanelContent>
        </Panel>
      </div>
    </div>
  );
}
