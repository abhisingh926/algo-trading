"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartFrame, ChartTooltipBox } from "@/components/charts/chart-frame";
import { ErrorState } from "@/components/tables/states";
import { EmptyState } from "@/components/tables/states";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useScoreHistory } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { formatScore, istStamp } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ScoreChange } from "@/types/research";

interface Point {
  t: number;
  score: number | null;
  confidence: number;
  direction: string;
  risk: string;
}

const signedScore = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${Math.round(v * 100) / 100}`;
const deltaClass = (v: number | null | undefined) =>
  v === null || v === undefined || v === 0 ? "text-muted-foreground" : v > 0 ? "text-profit" : "text-loss";

function ChangeCard({ change }: { change: ScoreChange }) {
  return (
    <li className="rounded-lg border bg-card p-4">
      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
        <span className="text-muted-foreground">
          {istStamp(change.from_as_of)} → {istStamp(change.to_as_of)}
        </span>
        <span className="tabular font-semibold">
          {formatScore(change.from_score)} → {formatScore(change.to_score)}
        </span>
        <span className={cn("tabular font-semibold", deltaClass(change.delta))}>{signedScore(change.delta)}</span>
      </p>
      {change.reasons.length > 0 ? (
        <ul className="mt-2 grid list-disc gap-1 pl-5 text-sm">
          {change.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">No specific reasons were recorded for this change.</p>
      )}
      {change.component_changes.length > 0 ? (
        <div className="mt-3 overflow-x-auto rounded-md border">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow className="hover:bg-transparent">
                {["Component", "From", "To", "Change"].map((h, i) => (
                  <TableHead
                    key={h}
                    className={cn("h-8 text-xs text-muted-foreground uppercase", i > 0 && "text-right")}
                  >
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {change.component_changes.map((c) => (
                <TableRow key={c.key}>
                  <TableCell>{c.label}</TableCell>
                  <TableCell className="tabular text-right">{c.from_points.toFixed(2)}</TableCell>
                  <TableCell className="tabular text-right">{c.to_points.toFixed(2)}</TableCell>
                  <TableCell className={cn("tabular text-right font-medium", deltaClass(c.delta))}>
                    {signedScore(c.delta)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </li>
  );
}

export function ScoreHistoryPanel({ symbol, title = "Score history" }: { symbol: string; title?: string }) {
  const { data, isLoading, error, refetch } = useScoreHistory(symbol);
  const points: Point[] = useMemo(
    () =>
      (data?.points ?? [])
        .map((p) => ({
          t: new Date(p.as_of).getTime(),
          score: p.research_score,
          confidence: p.data_confidence,
          direction: p.direction,
          risk: p.risk_level,
        }))
        .sort((a, b) => a.t - b.t),
    [data],
  );

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error && !data) {
    const none = error instanceof ApiError && error.code === 404;
    return (
      <div className="rounded-lg border bg-card">
        {none ? (
          <EmptyState
            title={`No score history for ${symbol}`}
            description="History appears once the symbol has been researched."
          />
        ) : (
          <ErrorState error={error} onRetry={() => void refetch()} />
        )}
      </div>
    );
  }

  const renderTip = ({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: Point }> }) => {
    const p = payload?.[0]?.payload;
    if (!active || !p) return null;
    return (
      <ChartTooltipBox
        title={`${istStamp(new Date(p.t).toISOString())}`}
        rows={[
          { label: "Research Score", value: formatScore(p.score) },
          { label: "Data Confidence", value: formatScore(p.confidence) },
          { label: "Direction", value: p.direction },
          { label: "Risk", value: p.risk },
        ]}
      />
    );
  };

  return (
    <section aria-label={title} className="grid gap-3">
      <h2 className="text-base font-semibold">{title}</h2>
      <ChartFrame
        title="Research Score and Data Confidence over runs"
        subtitle="One point per research run. Both use the same 0 to 100 scale."
        actions={
          <ul className="flex items-center gap-3 text-xs text-muted-foreground" aria-label="Legend">
            <li className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-[var(--chart-1)]" aria-hidden /> Research Score
            </li>
            <li className="flex items-center gap-1.5">
              <svg width="16" height="2" aria-hidden>
                <line
                  x1="0"
                  y1="1"
                  x2="16"
                  y2="1"
                  stroke="var(--muted-foreground)"
                  strokeWidth="2"
                  strokeDasharray="4 3"
                />
              </svg>
              Data Confidence
            </li>
          </ul>
        }
        isEmpty={points.length === 0}
        emptyTitle="No history yet"
        emptyDescription="Each research run adds a point."
        heightClass="h-56"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              padding={{ left: 12, right: 12 }}
              tickFormatter={(t: number) => formatDate(new Date(t)).slice(0, 6)}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              minTickGap={40}
            />
            <YAxis
              width={32}
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              content={renderTip}
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={{ r: 3, stroke: "var(--card)", strokeWidth: 2 }}
              connectNulls
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="confidence"
              stroke="var(--muted-foreground)"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3, stroke: "var(--card)", strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Explained changes ({data?.changes.length ?? 0})</h3>
        {data && data.changes.length > 0 ? (
          <ul className="grid gap-3">
            {[...data.changes].reverse().map((c) => (
              <ChangeCard key={`${c.from_run_id}-${c.to_run_id}`} change={c} />
            ))}
          </ul>
        ) : (
          <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            No score changes to explain yet. Once this stock has been researched in two or more runs, each change is
            listed here with the reasons behind it.
          </p>
        )}
      </div>
    </section>
  );
}
