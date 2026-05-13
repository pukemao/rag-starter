import { useMutation } from "@tanstack/react-query";
import { Loader2, MessageSquareText, Send } from "lucide-react";
import { useState, type FormEvent } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Field } from "@/components/Field";
import { ResultBlock } from "@/components/ResultBlock";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { Textarea } from "@/components/ui/textarea";
import { chatWithRag } from "@/lib/api";
import { parseOptionalJson } from "@/lib/form";

export function RagChatPage() {
  const [question, setQuestion] = useState("");
  const [k, setK] = useState(4);
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [filter, setFilter] = useState("");
  const [formError, setFormError] = useState("");

  const mutation = useMutation({
    mutationFn: chatWithRag
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    try {
      mutation.mutate({
        question,
        k,
        temperature,
        max_tokens: maxTokens,
        filter: parseOptionalJson(filter)
      });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "过滤条件格式错误");
    }
  }

  const result = mutation.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">RAG 增强对话</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          输入问题后，系统会先检索本地知识库，再把原始问题和参考段落合成 prompt 发给 DeepSeek。
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        <Panel>
          <PanelHeader>
            <PanelTitle>对话参数</PanelTitle>
            <PanelDescription>需要后端已配置 DeepSeek API Key</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <form className="space-y-5" onSubmit={onSubmit}>
              <Field label="问题" htmlFor="rag-question">
                <Textarea id="rag-question" value={question} onChange={(event) => setQuestion(event.target.value)} required />
              </Field>

              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="k" htmlFor="rag-k">
                  <Input id="rag-k" type="number" min={1} value={k} onChange={(event) => setK(Number(event.target.value))} />
                </Field>
                <Field label="temperature" htmlFor="rag-temperature">
                  <Input
                    id="rag-temperature"
                    type="number"
                    step={0.1}
                    min={0}
                    value={temperature}
                    onChange={(event) => setTemperature(Number(event.target.value))}
                  />
                </Field>
                <Field label="max tokens" htmlFor="rag-max-tokens">
                  <Input
                    id="rag-max-tokens"
                    type="number"
                    min={1}
                    value={maxTokens}
                    onChange={(event) => setMaxTokens(Number(event.target.value))}
                  />
                </Field>
              </div>

              <Field label="过滤条件" htmlFor="rag-filter" description='例如 {"source":"report.pdf"}'>
                <Textarea
                  id="rag-filter"
                  className="min-h-24 font-mono text-xs"
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                />
              </Field>

              {formError ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{formError}</p> : null}
              {mutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{mutation.error.message}</p> : null}

              <Button className="w-full" type="submit" disabled={!question.trim() || mutation.isPending}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                生成回答
              </Button>
            </form>
          </PanelContent>
        </Panel>

        <div className="space-y-6">
          <Panel>
            <PanelHeader>
              <PanelTitle>模型回答</PanelTitle>
              <PanelDescription>{result ? `模型：${result.model}` : "等待生成"}</PanelDescription>
            </PanelHeader>
            <PanelContent>
              {!result ? (
                <EmptyState
                  title="暂无回答"
                  description="提交问题后，这里会展示 DeepSeek 基于本地知识库生成的回答。"
                  action={<MessageSquareText className="h-5 w-5 text-muted-foreground" aria-hidden="true" />}
                />
              ) : (
                <div className="space-y-4">
                  <div className="rounded-lg border bg-background p-4">
                    <div className="mb-3 flex flex-wrap gap-2">
                      <Badge>references {result.references.length}</Badge>
                      <Badge variant="outline">{result.model}</Badge>
                    </div>
                    <p className="whitespace-pre-wrap text-sm leading-7">{result.answer}</p>
                  </div>

                  <details>
                    <summary className="cursor-pointer text-sm font-medium text-muted-foreground">查看最终 prompt</summary>
                    <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-muted p-4 text-xs leading-5 app-scrollbar">
                      {result.prompt}
                    </pre>
                  </details>
                </div>
              )}
            </PanelContent>
          </Panel>

          <Panel>
            <PanelHeader>
              <PanelTitle>参考段落</PanelTitle>
              <PanelDescription>LLM 回答使用的检索上下文</PanelDescription>
            </PanelHeader>
            <PanelContent>
              {result?.references.length ? (
                <div className="space-y-4">
                  {result.references.map((reference) => (
                    <ResultBlock key={`${reference.index}-${reference.page_content}`} result={reference} index={reference.index} />
                  ))}
                </div>
              ) : (
                <EmptyState title="暂无参考段落" description="生成回答后会展示被送入 prompt 的 top-k 段落。" />
              )}
            </PanelContent>
          </Panel>
        </div>
      </div>
    </div>
  );
}
