"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartFrame, ChartTooltipBox } from "@/components/charts/chart-frame";
import { EvidenceSheet } from "@/components/research/report/evidence-sheet";
import { Pill } from "@/components/trading/badges";
import { formatDecimal } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ComponentRating, ResearchReport, ScoreComponent } from "@/types/research";

const RATING_BAR: Record<ComponentRating, string> = {
  EXCELLENT: "bg-profit",
  GOOD: "bg-profit/70",
  FAIR: "bg-warning",
  POOR: "bg-loss",
  UNAVAILABLE: "bg-muted",
};

function ComponentRow({ c, onOpen }: { c: ScoreComponent; onOpen: () => void }) {
  const pct = c.max_points > 0 ? Math.min(100, (c.points / c.max_points) * 100) : 0;
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="group grid w-full gap-1.5 rounded-md border border-transparent px-2 py-2 text-left transition-colors hover:border-border hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        aria-label={`${c.label}: ${c.available ? `${c.points} of ${c.max_points} points` : "not assessed"}. Open evidence`}
      >
        <span className="flex items-baseline justify-between gap-3">
          <span className="flex items-center gap-2 text-sm font-medium">
            {c.label}
            {c.available ? (
              <span className="text-[11px] font-normal tracking-wide text-muted-foreground uppercase">{c.rating}</span>
            ) : (
              <Pill>Not assessed</Pill>
            )}
          </span>
          <span className="tabular flex items-center gap-1 text-sm">
            {c.available ? (
              <>
                <span className="font-semibold">{formatDecimal(c.points, 2)}</span>
                <span className="text-muted-foreground">/ {formatDecimal(c.max_points, 0)}</span>
              </>
            ) : (
              <span className="text-muted-foreground">max {formatDecimal(c.max_points, 0)}</span>
            )}
            <ChevronRight
              className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5"
              aria-hidden
            />
          </span>
        </span>
        <span
          className={cn(
            "h-2 overflow-hidden rounded-full",
            c.available ? "bg-muted" : "border border-dashed border-muted-foreground/40",
          )}
          aria-hidden
        >
          {c.available ? (
            <span className={cn("block h-full rounded-full", RATING_BAR[c.rating])} style={{ width: `${pct}%` }} />
          ) : null}
        </span>
        <span className="text-xs text-muted-foreground">{c.summary}</span>
      </button>
    </li>
  );
}

/** Short axis labels so nothing is clipped at the edges of the radar; the tooltip shows the full name. */
const SHORT_LABEL: Record<string, string> = {
  market_regime: "Market",
  liquidity: "Liquidity",
  price_action: "Price action",
  momentum: "Momentum",
  volume: "Volume",
  volatility: "Volatility",
  technical_setup: "Technical",
  news_catalyst: "News",
  historical_setup: "Historical",
  risk: "Risk",
};

interface RadarPoint {
  label: string;
  full: string;
  pct: number;
  points: number;
  max: number;
}

export function ScoreBreakdown({ report }: { report: ResearchReport }) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const { components } = report.score;
  const assessed = components.filter((c) => c.available);
  const notAssessed = components.filter((c) => !c.available);
  const radar: RadarPoint[] = assessed.map((c) => ({
    label: SHORT_LABEL[c.key] ?? c.label,
    full: c.label,
    pct: c.max_points > 0 ? Math.round((c.points / c.max_points) * 1000) / 10 : 0,
    points: c.points,
    max: c.max_points,
  }));
  const earned = assessed.reduce((s, c) => s + c.points, 0);
  const selected = components.find((c) => c.key === openKey) ?? null;

  const renderTip = ({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: RadarPoint }> }) => {
    const p = payload?.[0]?.payload;
    if (!active || !p) return null;
    return (
      <ChartTooltipBox
        title={p.full}
        rows={[
          { label: "Points", value: `${formatDecimal(p.points, 2)} / ${formatDecimal(p.max, 0)}` },
          { label: "Of maximum", value: `${p.pct}%` },
        ]}
      />
    );
  };

  return (
    <section aria-label="Score breakdown" className="grid gap-3">
      <div>
        <h2 className="text-base font-semibold">Score Breakdown</h2>
        <p className="text-xs text-muted-foreground">
          The Research Score is the points earned by the components that could be assessed, scaled to 100:{" "}
          <span className="tabular">
            {formatDecimal(earned, 1)} of {formatDecimal(report.score.available_points, 0)} assessable points
          </span>
          . Click a component to see the evidence and sources behind it.
        </p>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <ul className="rounded-lg border bg-card p-2" aria-label="Score components">
          {components.map((c) => (
            <ComponentRow key={c.key} c={c} onOpen={() => setOpenKey(c.key)} />
          ))}
        </ul>
        <ChartFrame
          title="Component profile"
          subtitle={
            notAssessed.length > 0
              ? `Assessed components only, as a share of their maximum. Not shown (not assessed): ${notAssessed.map((c) => c.label).join(", ")}.`
              : "Each component as a share of its maximum points."
          }
          isEmpty={radar.length < 3}
          emptyTitle="Too few assessed components to draw a profile"
          heightClass="h-80"
        >
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radar} outerRadius="58%" margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
              <Tooltip content={renderTip} isAnimationActive={false} />
              <Radar
                dataKey="pct"
                stroke="var(--chart-1)"
                strokeWidth={2}
                fill="var(--chart-1)"
                fillOpacity={0.25}
                isAnimationActive={false}
              />
            </RadarChart>
          </ResponsiveContainer>
        </ChartFrame>
      </div>
      <EvidenceSheet
        component={selected}
        sources={report.sources}
        onOpenChange={(o) => {
          if (!o) setOpenKey(null);
        }}
      />
    </section>
  );
}
