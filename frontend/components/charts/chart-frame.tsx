"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/tables/states";
import { cn } from "@/lib/utils";

interface ChartFrameProps {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  heightClass?: string;
  className?: string;
  children: React.ReactNode;
}

export function ChartFrame({
  title,
  subtitle,
  actions,
  isLoading,
  error,
  onRetry,
  isEmpty,
  emptyTitle = "No data yet",
  emptyDescription,
  heightClass = "h-64",
  className,
  children,
}: ChartFrameProps) {
  return (
    <figure className={cn("min-w-0 rounded-lg border bg-card p-4", className)}>
      <figcaption className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {subtitle ? <p className="text-xs text-muted-foreground">{subtitle}</p> : null}
        </div>
        {actions}
      </figcaption>
      <div className={cn("w-full", heightClass)}>
        {isLoading ? (
          <Skeleton className="size-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={onRetry} className="h-full py-0" />
        ) : isEmpty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} className="h-full py-0" />
        ) : (
          children
        )}
      </div>
    </figure>
  );
}

export function ChartTooltipBox({ title, rows }: { title: string; rows: { label: string; value: string }[] }) {
  return (
    <div className="rounded-md border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md">
      <p className="mb-0.5 text-muted-foreground">{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="tabular flex justify-between gap-4">
          <span className="text-muted-foreground">{r.label}</span>
          <span className="font-medium">{r.value}</span>
        </p>
      ))}
    </div>
  );
}
