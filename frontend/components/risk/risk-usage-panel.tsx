"use client";

import { CheckCircle2, OctagonX, ShieldAlert } from "lucide-react";
import { KillSwitchButton, ResumeTradingButton } from "@/components/layout/kill-switch";
import { ErrorState } from "@/components/tables/states";
import { Pill } from "@/components/trading/badges";
import { Skeleton } from "@/components/ui/skeleton";
import { useRiskConfig, useRiskStatus } from "@/hooks/use-risk";
import { formatDateTime, formatINR, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RiskUsage } from "@/types";

const fmt = (u: RiskUsage, v: number) => (u.unit === "INR" ? formatINR(v, { whole: true }) : formatNumber(v));

function UsageBar({ usage }: { usage: RiskUsage }) {
  const pct = Math.max(0, Math.min(1, usage.utilization)) * 100;
  const tone = usage.breached ? "bg-loss" : usage.utilization >= 0.8 ? "bg-warning" : "bg-profit";
  return (
    <li className={cn("rounded-md border p-3", usage.breached && "border-loss/50 bg-loss/10")}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <p className="flex items-center gap-2 text-sm font-medium">
          {usage.label}
          {usage.breached ? <Pill tone="bad">Breached</Pill> : null}
        </p>
        <p className="tabular text-sm">
          <span className={cn("font-medium", usage.breached && "text-loss")}>{fmt(usage, usage.current)}</span>
          <span className="text-muted-foreground"> / {fmt(usage, usage.limit)}</span>
        </p>
      </div>
      <div
        role="progressbar"
        aria-label={usage.label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pct)}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"
      >
        <div className={cn("h-full rounded-full transition-[width]", tone)} style={{ width: `${pct}%` }} />
      </div>
      <p className="tabular mt-1 text-right text-xs text-muted-foreground">{Math.round(usage.utilization * 100)}% used</p>
    </li>
  );
}

export function RiskUsagePanel() {
  const { data, isLoading, error, refetch } = useRiskStatus();
  const config = useRiskConfig();

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="grid gap-4">
      <div
        className={cn(
          "rounded-lg border p-4",
          data.trading_allowed ? "bg-card" : "border-loss/50 bg-loss/10",
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          {data.trading_allowed ? (
            <CheckCircle2 className="size-5 text-profit" aria-hidden />
          ) : (
            <ShieldAlert className="size-5 text-loss" aria-hidden />
          )}
          <h3 className="text-sm font-semibold">
            {data.trading_allowed ? "Trading allowed" : "Trading blocked"}
          </h3>
          <Pill tone={data.system_state === "RUNNING" ? "good" : "bad"} dot>
            {data.system_state}
          </Pill>
        </div>
        {data.blocked_reasons.length > 0 ? (
          <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-loss">
            {data.blocked_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">All risk limits are within bounds.</p>
        )}
      </div>

      {data.usage.length > 0 ? (
        <ul className="grid gap-2">
          {data.usage.map((u) => (
            <UsageBar key={u.key} usage={u} />
          ))}
        </ul>
      ) : (
        <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">No limit usage reported.</p>
      )}

      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2">
          <OctagonX className="size-4 text-loss" aria-hidden />
          <h3 className="text-sm font-semibold">Kill switch</h3>
          <Pill tone={data.kill_switch_active ? "bad" : "neutral"}>{data.kill_switch_active ? "Active" : "Inactive"}</Pill>
        </div>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {data.kill_switch_active
            ? `Activated ${formatDateTime(config.data?.kill_switch_activated_at)} IST${
                config.data?.kill_switch_reason ? `. Reason: ${config.data.kill_switch_reason}` : ""
              }`
            : "Stops all strategies, blocks new orders and cancels pending orders in one action."}
        </p>
        <div className="mt-3">{data.kill_switch_active ? <ResumeTradingButton /> : <KillSwitchButton />}</div>
      </div>
    </div>
  );
}
