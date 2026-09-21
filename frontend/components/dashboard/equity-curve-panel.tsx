"use client";

import { useMemo, useState } from "react";
import { ChartFrame } from "@/components/charts/chart-frame";
import { TimeSeriesChart, type SeriesPoint } from "@/components/charts/time-series-chart";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDashboardPnl } from "@/hooks/use-dashboard";
import { formatINR, formatINRCompact, formatPnl } from "@/lib/format";

const RANGES = [7, 30, 90] as const;

export function EquityCurvePanel({ className }: { className?: string }) {
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, error, refetch } = useDashboardPnl(days);

  const { points, mode } = useMemo((): { points: SeriesPoint[]; mode: "equity" | "cumulative" } => {
    if (data && data.equity_curve.length > 0) {
      return {
        mode: "equity",
        points: data.equity_curve
          .map((p) => ({ t: new Date(p.timestamp).getTime(), value: p.equity }))
          .sort((a, b) => a.t - b.t),
      };
    }
    // Fallback: cumulative daily net P&L when there are no equity snapshots yet.
    let running = 0;
    const daily = [...(data?.daily ?? [])].sort((a, b) => a.date.localeCompare(b.date));
    return {
      mode: "cumulative",
      points: daily.map((d) => {
        running += d.net_pnl;
        return { t: new Date(`${d.date}T12:00:00Z`).getTime(), value: running };
      }),
    };
  }, [data]);

  return (
    <ChartFrame
      className={className}
      title={mode === "equity" ? "Equity Curve" : "Cumulative Net P&L"}
      subtitle={
        mode === "equity"
          ? `Account equity, last ${days} days`
          : `No equity snapshots yet: showing cumulative daily net P&L, last ${days} days`
      }
      actions={
        <Tabs value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <TabsList>
            {RANGES.map((r) => (
              <TabsTrigger key={r} value={String(r)}>
                {r}D
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      }
      isLoading={isLoading}
      error={data ? null : error}
      onRetry={() => void refetch()}
      isEmpty={points.length === 0}
      emptyTitle="No P&L history yet"
      emptyDescription="The equity curve appears once strategies or manual orders have produced trades."
      heightClass="h-72"
    >
      <TimeSeriesChart
        data={points}
        label={mode === "equity" ? "Equity" : "Net P&L"}
        formatValue={mode === "equity" ? (v) => formatINR(v) : (v) => formatPnl(v)}
        formatAxis={formatINRCompact}
        baseline={mode === "cumulative" ? 0 : undefined}
        dateOnly={mode === "cumulative"}
      />
    </ChartFrame>
  );
}
