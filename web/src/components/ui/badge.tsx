import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "outline";

const variants: Record<BadgeVariant, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-800",
  outline: "border bg-surface text-muted-foreground"
};

export function Badge({
  className,
  variant = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn("inline-flex min-h-6 items-center rounded-md px-2 py-0.5 text-xs font-medium", variants[variant], className)}
      {...props}
    />
  );
}
