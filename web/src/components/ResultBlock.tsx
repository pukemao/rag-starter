import { Badge } from "@/components/ui/badge";
import { formatScore } from "@/lib/utils";
import type { SearchResult } from "@/types/api";

type ResultBlockProps = {
  result: SearchResult;
  index: number;
};

export function ResultBlock({ result, index }: ResultBlockProps) {
  const source = result.metadata.source ?? result.metadata.source_id ?? "unknown";

  return (
    <article className="rounded-lg border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">#{index}</Badge>
        <Badge>{String(source)}</Badge>
        <Badge variant="warning">score {formatScore(result.score)}</Badge>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">{result.page_content}</p>
      <details className="mt-3">
        <summary className="cursor-pointer text-xs font-medium text-muted-foreground">metadata</summary>
        <pre className="mt-2 overflow-auto rounded-md bg-muted p-3 text-xs leading-5 text-muted-foreground app-scrollbar">
          {JSON.stringify(result.metadata, null, 2)}
        </pre>
      </details>
    </article>
  );
}
