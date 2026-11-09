import type { ReactNode } from "react";
import { AlertCircle, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border p-8 text-center">
      <Inbox aria-hidden className="size-5 text-muted-foreground" />
      <p className="font-medium">{title}</p>
      {hint && <p className="max-w-prose text-sm text-muted-foreground">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retryLabel, onRetry }: { message: string; retryLabel?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 rounded-md border border-status-excess/40 bg-status-excess-bg p-6 text-center text-status-excess">
      <AlertCircle aria-hidden className="size-5" />
      <p className="text-sm">{message}</p>
      {onRetry && <Button variant="outline" size="sm" onClick={onRetry}>{retryLabel}</Button>}
    </div>
  );
}
