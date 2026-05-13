import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, FileText, FileUp, Loader2, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useMemo, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ResultBlock } from "@/components/ResultBlock";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { Textarea } from "@/components/ui/textarea";
import { deleteDocuments, indexFiles, listDocuments, searchKnowledgeBase } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { KnowledgeFile } from "@/types/api";

const documentsQueryKey = ["documents"];

export function KnowledgeBasePage() {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [k, setK] = useState(2);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [isDraggingFiles, setIsDraggingFiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const documentsQuery = useQuery({
    queryKey: documentsQueryKey,
    queryFn: listDocuments
  });

  const uploadMutation = useMutation({
    mutationFn: indexFiles,
    onSuccess: () => {
      setFiles([]);
      setUploadOpen(false);
      void queryClient.invalidateQueries({ queryKey: documentsQueryKey });
    }
  });

  const searchMutation = useMutation({
    mutationFn: searchKnowledgeBase
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocuments,
    onSuccess: async (_, variables) => {
      if (variables.source_id === selectedSource || variables.source === selectedSource) {
        setSelectedSource(null);
      }
      await queryClient.invalidateQueries({ queryKey: documentsQueryKey });
    }
  });

  const documents = documentsQuery.data?.files ?? [];
  const selectedFile = documents.find((file) => file.source_id === selectedSource || file.source === selectedSource) ?? null;
  const totalSize = useMemo(() => files.reduce((sum, file) => sum + file.size, 0), [files]);
  const results = searchMutation.data?.results ?? [];

  function onUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!files.length) {
      return;
    }
    uploadMutation.mutate({
      files,
      splitterType: "recursive",
      chunkSize: 1000,
      chunkOverlap: 200
    });
  }

  function addFiles(fileList: FileList | File[]) {
    const nextFiles = Array.from(fileList);
    if (!nextFiles.length) {
      return;
    }
    setFiles((currentFiles) => {
      const merged = [...currentFiles];
      const seen = new Set(currentFiles.map(fileKey));
      for (const file of nextFiles) {
        const key = fileKey(file);
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(file);
        }
      }
      return merged;
    });
  }

  function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    addFiles(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
  }

  function onUploadDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setIsDraggingFiles(false);
    addFiles(event.dataTransfer.files);
  }

  function removeSelectedFile(targetFile: File) {
    setFiles((currentFiles) => currentFiles.filter((file) => fileKey(file) !== fileKey(targetFile)));
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }
    searchMutation.mutate({
      query: trimmed,
      k,
      filter: selectedFile?.source_id ? { source_id: selectedFile.source_id } : selectedSource ? { source: selectedSource } : null
    });
  }

  function onDelete(file: KnowledgeFile) {
    const confirmed = window.confirm(`确认删除知识库文件「${file.filename}」及其 ${file.chunk_count} 个文本块？`);
    if (!confirmed) {
      return;
    }
    deleteMutation.mutate(file.source_id ? { source_id: file.source_id } : { source: file.source });
  }

  function openSearch(file?: KnowledgeFile) {
    if (file) {
      setSelectedSource(file.source_id ?? file.source);
    }
    searchMutation.reset();
    setSearchOpen(true);
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <Badge variant="outline">Knowledge Base</Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-foreground sm:text-3xl">知识库</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            管理本地知识库文件。主页面聚焦文件列表，上传、查询和删除通过明确操作完成。
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button onClick={() => setUploadOpen(true)}>
            <FileUp className="h-4 w-4" aria-hidden="true" />
            上传文件
          </Button>
          <Button variant="secondary" onClick={() => openSearch()}>
            <Search className="h-4 w-4" aria-hidden="true" />
            查询知识库
          </Button>
          <Button variant="outline" onClick={() => void documentsQuery.refetch()} disabled={documentsQuery.isFetching}>
            {documentsQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-4 w-4" aria-hidden="true" />}
            刷新
          </Button>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <Metric label="文件数量" value={documentsQuery.data?.total_files ?? 0} />
        <Metric label="文本块数量" value={documentsQuery.data?.total_chunks ?? 0} />
        <Metric label="查询范围" value={selectedFile ? selectedFile.filename : "全部文件"} />
      </section>

      <Panel>
        <PanelHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <PanelTitle>文件列表</PanelTitle>
            <PanelDescription>已入库文件及其向量文本块数量</PanelDescription>
          </div>
          {selectedFile ? (
            <Button variant="ghost" size="sm" onClick={() => setSelectedSource(null)}>
              <X className="h-4 w-4" aria-hidden="true" />
              清除查询范围
            </Button>
          ) : null}
        </PanelHeader>
        <PanelContent className="p-0">
          <DocumentTable
            documents={documents}
            selectedSource={selectedSource}
            isLoading={documentsQuery.isLoading}
            error={documentsQuery.error}
            deletingSource={deleteMutation.variables?.source_id ?? deleteMutation.variables?.source ?? null}
            isDeleting={deleteMutation.isPending}
            onSelect={(file) => setSelectedSource(file.source_id ?? file.source)}
            onSearch={openSearch}
            onDelete={onDelete}
          />
        </PanelContent>
      </Panel>

      <Dialog
        open={uploadOpen}
        title="上传知识库文件"
        description="拖拽文件到上传区，或点击上传区选择文件，支持批量上传。"
        onClose={() => setUploadOpen(false)}
      >
        <form className="space-y-5" onSubmit={onUpload}>
          <input ref={fileInputRef} className="sr-only" type="file" multiple onChange={onFileInputChange} />
          <button
            type="button"
            className={cn(
              "flex min-h-56 w-full flex-col items-center justify-center rounded-lg border border-dashed bg-background p-6 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isDraggingFiles ? "border-primary bg-primary/5 text-primary" : "border-input hover:border-primary hover:bg-primary/5"
            )}
            onClick={() => fileInputRef.current?.click()}
            onDragEnter={(event) => {
              event.preventDefault();
              setIsDraggingFiles(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              if (event.currentTarget === event.target) {
                setIsDraggingFiles(false);
              }
            }}
            onDrop={onUploadDrop}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-md bg-primary/10 text-primary">
              <FileUp className="h-6 w-6" aria-hidden="true" />
            </span>
            <span className="mt-4 text-base font-semibold">{isDraggingFiles ? "松开后添加文件" : "拖拽文件到这里上传"}</span>
            <span className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
              点击此区域同样可以打开文件选择器，支持批量选择。重复文件会在上传前自动合并。
            </span>
          </button>

          {files.length ? (
            <div className="rounded-md border bg-background p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-medium text-muted-foreground">
                  已选择 {files.length} 个文件，共 {Math.max(1, Math.round(totalSize / 1024))} KB
                </p>
                <Button variant="ghost" size="sm" type="button" onClick={() => setFiles([])}>
                  清空
                </Button>
              </div>
              <ul className="mt-3 space-y-2">
                {files.map((file) => (
                  <li key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3 text-sm">
                    <span className="min-w-0">
                      <span className="block break-words">{file.name}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">{Math.max(1, Math.round(file.size / 1024))} KB</span>
                    </span>
                    <Button variant="ghost" size="icon" type="button" aria-label={`移除 ${file.name}`} onClick={() => removeSelectedFile(file)}>
                      <X className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {uploadMutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{uploadMutation.error.message}</p> : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" type="button" onClick={() => setUploadOpen(false)}>
              取消
            </Button>
            <Button type="submit" disabled={!files.length || uploadMutation.isPending}>
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Database className="h-4 w-4" aria-hidden="true" />}
              上传并入库
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={searchOpen}
        title="查询知识库"
        description={selectedFile ? `当前查询范围：${selectedFile.filename}` : "当前查询范围：全部文件"}
        onClose={() => setSearchOpen(false)}
        size="wide"
      >
        <form className="space-y-5" onSubmit={onSearch}>
          <label className="space-y-2">
            <span className="text-sm font-medium">问题或关键词</span>
            <Textarea
              className="min-h-28"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="输入要查询的内容"
              required
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium">返回段落数</span>
            <Input type="number" min={1} value={k} onChange={(event) => setK(Number(event.target.value))} />
          </label>

          {selectedFile ? (
            <div className="rounded-md border bg-background p-3 text-sm">
              <p className="font-medium">已限定文件</p>
              <p className="mt-1 break-words text-muted-foreground">{selectedFile.filename}</p>
            </div>
          ) : null}

          {searchMutation.error ? <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{searchMutation.error.message}</p> : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" type="button" onClick={() => setSearchOpen(false)}>
              取消
            </Button>
            <Button type="submit" disabled={!query.trim() || searchMutation.isPending}>
              {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Search className="h-4 w-4" aria-hidden="true" />}
              查询
            </Button>
          </div>
        </form>

        {searchMutation.data ? (
          <div className="mt-6 border-t pt-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">查询结果</h3>
                <p className="mt-1 text-sm text-muted-foreground">返回 {results.length} 个匹配段落</p>
              </div>
            </div>
            {results.length ? (
              <div className="space-y-4">
                {results.map((result, index) => (
                  <ResultBlock key={`${result.page_content}-${index}`} result={result} index={index + 1} />
                ))}
              </div>
            ) : (
              <EmptyState title="没有匹配结果" description="可以切换到全部文件或调整查询问题。" />
            )}
          </div>
        ) : null}
      </Dialog>
    </div>
  );
}

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function DocumentTable({
  documents,
  selectedSource,
  isLoading,
  error,
  deletingSource,
  isDeleting,
  onSelect,
  onSearch,
  onDelete
}: {
  documents: KnowledgeFile[];
  selectedSource: string | null;
  isLoading: boolean;
  error: Error | null;
  deletingSource: string | null;
  isDeleting: boolean;
  onSelect: (file: KnowledgeFile) => void;
  onSearch: (file: KnowledgeFile) => void;
  onDelete: (file: KnowledgeFile) => void;
}) {
  if (isLoading) {
    return (
      <div className="flex min-h-56 items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        正在加载知识库文件
      </div>
    );
  }

  if (error) {
    return <div className="m-5 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error.message}</div>;
  }

  if (!documents.length) {
    return (
      <div className="p-5">
        <EmptyState title="暂无知识库文件" description="点击右上角上传文件，完成入库后会在这里展示。" />
      </div>
    );
  }

  return (
    <div className="overflow-x-auto app-scrollbar">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead className="border-b bg-muted/60 text-xs text-muted-foreground">
          <tr>
            <th className="px-5 py-3 font-medium">文件</th>
            <th className="px-4 py-3 font-medium">文本块</th>
            <th className="px-4 py-3 font-medium">Source ID</th>
            <th className="px-5 py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((file) => {
            const active = selectedSource === file.source_id || selectedSource === file.source;
            const deleting = isDeleting && (deletingSource === file.source_id || deletingSource === file.source);
            return (
              <tr key={file.source_id ?? file.file_hash ?? file.source} className={cn("border-b last:border-0", active && "bg-primary/5")}>
                <td className="px-5 py-4">
                  <button
                    type="button"
                    className="flex min-h-11 max-w-[360px] items-center gap-3 text-left font-medium text-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => onSelect(file)}
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <FileText className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0">
                      <span className="block break-words">{file.filename}</span>
                      <span className="mt-0.5 block break-all text-xs font-normal text-muted-foreground">{file.source}</span>
                    </span>
                  </button>
                </td>
                <td className="px-4 py-4">
                  <Badge>{file.chunk_count}</Badge>
                </td>
                <td className="max-w-[200px] px-4 py-4 font-mono text-xs text-muted-foreground">
                  <span className="break-all">{file.source_id ?? "-"}</span>
                </td>
                <td className="px-5 py-4">
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => onSearch(file)}>
                      <Search className="h-4 w-4" aria-hidden="true" />
                      查询
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => onDelete(file)} disabled={isDeleting}>
                      {deleting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
                      删除
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-surface p-4 shadow-sm">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-xl font-semibold text-foreground">{value}</p>
    </div>
  );
}
