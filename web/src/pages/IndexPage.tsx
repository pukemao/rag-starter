import { useMutation } from "@tanstack/react-query";
import { FileUp, Loader2 } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { indexFiles } from "@/lib/api";
import type { IndexResponse } from "@/types/api";

export function IndexPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [splitterType, setSplitterType] = useState("recursive");
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [lastResult, setLastResult] = useState<IndexResponse | null>(null);

  const totalSize = useMemo(() => files.reduce((sum, file) => sum + file.size, 0), [files]);

  const mutation = useMutation({
    mutationFn: indexFiles,
    onSuccess: (result) => setLastResult(result)
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!files.length) {
      return;
    }
    mutation.mutate({ files, splitterType, chunkSize, chunkOverlap });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">知识库索引</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          上传一个或多个文件，后端会完成文档加载、分割、文件内去重和 Chroma 入库。
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        <Panel>
          <PanelHeader>
            <PanelTitle>上传配置</PanelTitle>
            <PanelDescription>重复文件会由后端返回 409 提示</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <form className="space-y-5" onSubmit={onSubmit}>
              <Field label="文件" htmlFor="files" description={`已选择 ${files.length} 个文件，共 ${Math.round(totalSize / 1024)} KB`}>
                <Input
                  id="files"
                  type="file"
                  multiple
                  onChange={(event) => setFiles(Array.from(event.currentTarget.files ?? []))}
                />
              </Field>

              <Field label="分割器" htmlFor="splitter-type">
                <Input id="splitter-type" value={splitterType} onChange={(event) => setSplitterType(event.target.value)} />
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Chunk Size" htmlFor="chunk-size">
                  <Input
                    id="chunk-size"
                    type="number"
                    min={1}
                    value={chunkSize}
                    onChange={(event) => setChunkSize(Number(event.target.value))}
                  />
                </Field>
                <Field label="Chunk Overlap" htmlFor="chunk-overlap">
                  <Input
                    id="chunk-overlap"
                    type="number"
                    min={0}
                    value={chunkOverlap}
                    onChange={(event) => setChunkOverlap(Number(event.target.value))}
                  />
                </Field>
              </div>

              {mutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{mutation.error.message}</p> : null}

              <Button className="w-full" type="submit" disabled={!files.length || mutation.isPending}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <FileUp className="h-4 w-4" aria-hidden="true" />}
                开始索引
              </Button>
            </form>
          </PanelContent>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>索引结果</PanelTitle>
            <PanelDescription>返回每个文件的 source_id、写入数量和去重数量</PanelDescription>
          </PanelHeader>
          <PanelContent>
            {!lastResult ? (
              <EmptyState title="尚未提交文件" description="选择文件并开始索引后，结果会显示在这里。" />
            ) : (
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-4">
                  <Metric label="文件数" value={lastResult.total_files} />
                  <Metric label="写入 chunks" value={lastResult.total_chunks} />
                  <Metric label="输入 chunks" value={lastResult.total_input_chunks} />
                  <Metric label="跳过重复" value={lastResult.total_skipped_duplicates} />
                </div>
                <div className="overflow-x-auto app-scrollbar">
                  <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                    <thead className="border-b text-xs text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-medium">文件名</th>
                        <th className="py-3 pr-4 font-medium">source_id</th>
                        <th className="py-3 pr-4 font-medium">写入</th>
                        <th className="py-3 pr-4 font-medium">输入</th>
                        <th className="py-3 pr-4 font-medium">去重</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lastResult.files.map((file) => (
                        <tr key={file.source_id} className="border-b last:border-0">
                          <td className="py-3 pr-4 font-medium">{file.filename}</td>
                          <td className="py-3 pr-4 font-mono text-xs">{file.source_id}</td>
                          <td className="py-3 pr-4">{file.count}</td>
                          <td className="py-3 pr-4">{file.input_count}</td>
                          <td className="py-3 pr-4">{file.skipped_duplicates}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </PanelContent>
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}
