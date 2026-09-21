"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  OctagonAlert,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { errorText } from "@/lib/toast";
import { cn } from "@/lib/utils";
import type { ReviewCheck, ReviewSeverity, ReviewVerdict, StrategyReview } from "@/types";

const SEVERITY: Record<
  ReviewSeverity,
  { icon: LucideIcon; className: string; label: string; plural: string; rank: number }
> = {
  RISK: { icon: OctagonAlert, className: "text-loss", label: "Risk", plural: "risks", rank: 0 },
  WARN: { icon: AlertTriangle, className: "text-warning", label: "Warning", plural: "warnings", rank: 1 },
  INFO: { icon: Info, className: "text-info", label: "Info", plural: "notes", rank: 2 },
  GOOD: { icon: CheckCircle2, className: "text-profit", label: "Good", plural: "good", rank: 3 },
};

const VERDICT: Record<
  ReviewVerdict,
  { tone: "good" | "warn" | "bad"; icon: LucideIcon; label: string }
> = {
  RECOMMENDED: { tone: "good", icon: ShieldCheck, label: "Recommended" },
  CAUTION: { tone: "warn", icon: AlertTriangle, label: "Caution" },
  NOT_RECOMMENDED: { tone: "bad", icon: ShieldAlert, label: "Not recommended" },
};

export function VerdictBadge({ verdict, className }: { verdict: ReviewVerdict; className?: string }) {
  const v = VERDICT[verdict] ?? VERDICT.CAUTION;
  const Icon = v.icon;
  return (
    <Pill tone={v.tone} className={cn("h-6 px-2 text-xs", className)}>
      <Icon className="size-3.5" aria-hidden />
      {v.label}
    </Pill>
  );
}

/** Worst first. The backend already sorts this way; sorting again keeps the UI correct if it ever changes. */
function sortWorstFirst(checks: ReviewCheck[]): ReviewCheck[] {
  return checks
    .map((c, i) => ({ c, i }))
    .sort((a, b) => (SEVERITY[a.c.severity]?.rank ?? 9) - (SEVERITY[b.c.severity]?.rank ?? 9) || a.i - b.i)
    .map(({ c }) => c);
}

function CheckRow({ check, compact }: { check: ReviewCheck; compact: boolean }) {
  const sev = SEVERITY[check.severity] ?? SEVERITY.INFO;
  const Icon = sev.icon;
  return (
    <li className="flex gap-2.5">
      <Icon className={cn("mt-0.5 size-4 shrink-0", sev.className)} aria-hidden />
      <div className="min-w-0 text-sm">
        <p className="font-medium">
          <span className="sr-only">{sev.label}: </span>
          {check.title}
          {!compact ? (
            <span className="ml-2 text-[11px] font-normal tracking-wide text-muted-foreground uppercase">
              {sev.label} · {check.category}
            </span>
          ) : null}
        </p>
        {!compact && check.detail ? <p className="text-muted-foreground">{check.detail}</p> : null}
        {check.suggestion ? (
          <p className={cn("text-xs", compact ? "text-muted-foreground" : "mt-0.5 text-foreground/80")}>
            <span className="font-medium">Suggestion:</span> {check.suggestion}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function CountChip({ severity, count }: { severity: ReviewSeverity; count: number }) {
  const sev = SEVERITY[severity];
  const Icon = sev.icon;
  return (
    <span
      className={cn("inline-flex items-center gap-1 text-xs", count === 0 ? "text-muted-foreground/60" : sev.className)}
      title={`${count} ${sev.plural}`}
    >
      <Icon className="size-3.5" aria-hidden />
      <span className="tabular font-medium">{count}</span>
      <span className="text-muted-foreground">{sev.plural}</span>
    </span>
  );
}

interface StrategyReviewPanelProps {
  review: StrategyReview | undefined;
  isLoading?: boolean;
  /** A refetch is in flight (the previous review may still be shown). */
  isFetching?: boolean;
  error?: unknown;
  onRetry?: () => void;
  /** compact: verdict, counts and only the warnings/risks; full: every check with detail. */
  variant?: "compact" | "full";
  title?: string;
  /** Shown when there is nothing to review yet (for example an incomplete form). */
  placeholder?: React.ReactNode;
  className?: string;
}

/** Renders a StrategyReview from POST /strategies/review or GET /strategies/{id}/review. Purely advisory. */
export function StrategyReviewPanel({
  review,
  isLoading,
  isFetching,
  error,
  onRetry,
  variant = "full",
  title,
  placeholder,
  className,
}: StrategyReviewPanelProps) {
  const [showAll, setShowAll] = useState(false);
  const compact = variant === "compact";
  const checks = review ? sortWorstFirst(review.checks) : [];
  const attention = checks.filter((c) => c.severity === "RISK" || c.severity === "WARN");
  const visible = compact && !showAll ? attention.slice(0, 4) : checks;
  const hiddenCount = checks.length - visible.length;

  return (
    <section
      aria-label={title ?? "Good-practice review"}
      className={cn("rounded-lg border bg-card", compact ? "p-3" : "p-4", className)}
    >
      {title || isFetching ? (
        <div className="mb-2 flex items-center justify-between gap-2">
          {title ? <h3 className="text-sm font-semibold">{title}</h3> : <span />}
          {isFetching && review ? (
            <span role="status" className="flex items-center gap-1 text-xs text-muted-foreground">
              <Loader2 className="size-3 animate-spin" aria-hidden /> Updating…
            </span>
          ) : null}
        </div>
      ) : null}

      {isLoading && !review ? (
        <div className="grid gap-2" role="status" aria-label="Loading review">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : !review && error ? (
        <div className="text-sm" role="alert">
          <p className="font-medium">Review unavailable</p>
          <p className="text-xs text-muted-foreground">
            {errorText(error).title}. The review is advisory: you can carry on without it.
          </p>
          {onRetry ? (
            <Button variant="outline" size="xs" className="mt-2" onClick={onRetry}>
              <RefreshCw /> Retry
            </Button>
          ) : null}
        </div>
      ) : !review ? (
        <p className="text-sm text-muted-foreground">
          {placeholder ?? "Nothing to review yet."}
        </p>
      ) : (
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <VerdictBadge verdict={review.verdict} />
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <CountChip severity="RISK" count={review.counts.risk} />
              <CountChip severity="WARN" count={review.counts.warn} />
              <CountChip severity="INFO" count={review.counts.info} />
              <CountChip severity="GOOD" count={review.counts.good} />
            </div>
          </div>
          <p className="text-sm">{review.summary}</p>

          {visible.length > 0 ? (
            <ul className="grid gap-2.5">
              {visible.map((c) => (
                <CheckRow key={c.key} check={c} compact={compact && !showAll} />
              ))}
            </ul>
          ) : compact ? (
            <p className="text-xs text-muted-foreground">No warnings or risks found.</p>
          ) : null}

          {compact && (hiddenCount > 0 || showAll) ? (
            <Button
              variant="ghost"
              size="xs"
              className="justify-self-start"
              onClick={() => setShowAll((v) => !v)}
              aria-expanded={showAll}
            >
              {showAll ? "Show fewer checks" : `Show all ${checks.length} checks`}
            </Button>
          ) : null}

          {review.disclaimer ? (
            <p className="text-[11px] leading-snug text-muted-foreground">{review.disclaimer}</p>
          ) : null}
        </div>
      )}
    </section>
  );
}
