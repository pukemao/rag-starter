import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";

type FieldProps = {
  label: string;
  htmlFor: string;
  description?: string;
  error?: string;
  children: ReactNode;
};

export function Field({ label, htmlFor, description, error, children }: FieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {description ? <p className="text-xs leading-5 text-muted-foreground">{description}</p> : null}
      {error ? <p className="text-xs leading-5 text-destructive">{error}</p> : null}
    </div>
  );
}
