"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { errorText } from "@/lib/toast";
import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-1.5 px-4 py-10 text-center", className)}>
      <Inbox className="size-6 text-muted-foreground" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-md text-xs text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const { title, description } = errorText(error);
  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center justify-center gap-1.5 px-4 py-10 text-center", className)}
    >
      <AlertTriangle className="size-6 text-loss" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-md text-xs text-muted-foreground">{description}</p> : null}
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          <RefreshCw /> Retry
        </Button>
      ) : null}
    </div>
  );
}
