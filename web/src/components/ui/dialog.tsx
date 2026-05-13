import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type DialogProps = {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  size?: "default" | "wide";
};

export function Dialog({ open, title, description, children, onClose, size = "default" }: DialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/30 p-4 sm:items-center" role="presentation">
      <button className="absolute inset-0 cursor-default" type="button" aria-label="关闭弹窗" onClick={onClose} />
      <section
        className={cn(
          "relative max-h-[calc(100dvh-2rem)] w-full overflow-hidden rounded-lg border bg-surface text-surface-foreground shadow-lg",
          size === "wide" ? "max-w-4xl" : "max-w-xl"
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <div className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            <h2 id="dialog-title" className="text-base font-semibold">
              {title}
            </h2>
            {description ? <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p> : null}
          </div>
          <Button variant="ghost" size="icon" type="button" aria-label="关闭" onClick={onClose}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <div className="max-h-[calc(100dvh-9rem)] overflow-y-auto p-5 app-scrollbar">{children}</div>
      </section>
    </div>
  );
}
