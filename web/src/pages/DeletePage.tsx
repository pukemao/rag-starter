import { useMutation } from "@tanstack/react-query";
import { Loader2, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Field } from "@/components/Field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { Textarea } from "@/components/ui/textarea";
import { deleteDocuments } from "@/lib/api";

export function DeletePage() {
  const [source, setSource] = useState("");
  const [ids, setIds] = useState("");

  const mutation = useMutation({
    mutationFn: deleteDocuments
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedIds = ids
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
    mutation.mutate({
      source: source.trim() || null,
      ids: parsedIds.length ? parsedIds : null
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">删除向量数据</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          按 ids 精准删除，或按 metadata.source 删除某个上传文件对应的数据。
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        <Panel>
          <PanelHeader>
            <PanelTitle>删除条件</PanelTitle>
            <PanelDescription>ids 和 source 至少填写一项</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <form className="space-y-5" onSubmit={onSubmit}>
              <Field label="source" htmlFor="delete-source" description="通常是上传时的文件名，例如 report.pdf">
                <Input id="delete-source" value={source} onChange={(event) => setSource(event.target.value)} />
              </Field>
              <Field label="ids" htmlFor="delete-ids" description="多个 id 可用换行或英文逗号分隔">
                <Textarea id="delete-ids" className="font-mono text-xs" value={ids} onChange={(event) => setIds(event.target.value)} />
              </Field>

              {mutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{mutation.error.message}</p> : null}

              <Button className="w-full" variant="destructive" type="submit" disabled={(!source.trim() && !ids.trim()) || mutation.isPending}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
                删除数据
              </Button>
            </form>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>删除结果</PanelTitle>
            <PanelDescription>按 source 删除时，Chroma 不一定返回数量</PanelDescription>
          </PanelHeader>
          <PanelContent>
            {!mutation.data ? (
              <EmptyState title="尚未执行删除" description="提交删除请求后，这里会展示后端返回结果。" />
            ) : (
              <div className="rounded-lg border bg-background p-4">
                <Badge variant="success">success</Badge>
                <p className="mt-4 text-sm leading-6">
                  删除数量：
                  <span className="font-semibold">{mutation.data.deleted ?? "未返回"}</span>
                </p>
              </div>
            )}
          </PanelContent>
        </Panel>
      </div>
    </div>
  );
}
