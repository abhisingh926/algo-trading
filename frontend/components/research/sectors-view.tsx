"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartFrame, ChartTooltipBox } from "@/components/charts/chart-frame";
import { PageHeader } from "@/components/layout/page-header";
import { ResearchDisclaimer } from "@/components/research/disclaimer";
import { SyntheticDataBanner } from "@/components/research/banners";
import { TrendBadge } from "@/components/research/badges";
import { DataTable, type Column } from "@/components/tables/data-table";
import { useResearchSectors } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { formatPercent, pnlClass } from "@/lib/format";
import { dataAsOf, formatDecimal, formatMultiple, formatPct } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { SectorSnapshot } from "@/types/research";

const ret = (v: number | null) => (
  <span className={cn("tabular font-medium", pnlClass(v))}>{formatPercent(v, 2, true)}</span>
);

const columns: Column<SectorSnapshot>[] = [
  { key: "rank", header: "Rank", cell: (s) => <span className="tabular text-muted-foreground">{s.rank ?? "—"}</span> },
  {
    key: "sector",
    header: "Sector",
    cell: (s) => (
      <div>
        <span className="font-medium">{s.sector}</span>
        <span className="ml-2 text-xs text-muted-foreground">{s.constituents} scanned</span>
      </div>
    ),
  },
  { key: "r1", header: "1D return", align: "right", cell: (s) => ret(s.ret_1d_pct) },
  { key: "r5", header: "5D return", align: "right", cell: (s) => ret(s.ret_5d_pct) },
  {
    key: "rs1",
    header: "Rel. strength 1D",
    align: "right",
    cell: (s) => <span className="tabular">{formatDecimal(s.rel_strength_1d, 2)}</span>,
  },
  {
    key: "rs5",
    header: "Rel. strength 5D",
    align: "right",
    cell: (s) => <span className="tabular">{formatDecimal(s.rel_strength_5d, 2)}</span>,
  },
  {
    key: "rv",
    header: "Avg. rel. volume",
    align: "right",
    hideBelow: "md",
    cell: (s) => <span className="tabular">{formatMultiple(s.avg_rel_volume)}</span>,
  },
  {
    key: "breadth",
    header: "Breadth",
    align: "right",
    hideBelow: "md",
    cell: (s) => <span className="tabular">{formatPct(s.breadth_pct, 0)}</span>,
  },
  {
    key: "mom",
    header: "Momentum",
    align: "right",
    hideBelow: "lg",
    cell: (s) => <span className="tabular">{formatDecimal(s.momentum, 1)}</span>,
  },
  { key: "trend", header: "Trend", cell: (s) => <TrendBadge trend={s.trend} /> },
];

interface ChartRow {
  sector: string;
  rs1: number | null;
  rs5: number | null;
}

export function SectorsView() {
  const { data, isLoading, error, refetch } = useResearchSectors();
  const noRun = error instanceof ApiError && error.code === 404;
  const sectors = [...(data?.sectors ?? [])].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
  const chartData: ChartRow[] = sectors.map((s) => ({
    sector: s.sector,
    rs1: s.rel_strength_1d,
    rs5: s.rel_strength_5d,
  }));

  const renderTip = ({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: ChartRow }> }) => {
    const p = payload?.[0]?.payload;
    if (!active || !p) return null;
    return (
      <ChartTooltipBox
        title={p.sector}
        rows={[
          { label: "Relative strength 1D", value: formatDecimal(p.rs1, 2) },
          { label: "Relative strength 5D", value: formatDecimal(p.rs5, 2) },
        ]}
      />
    );
  };

  return (
    <>
      <PageHeader
        title="Sector Rotation"
        description={
          data
            ? `Run #${data.run_number} · ${dataAsOf(data.as_of)}. Computed over the stocks scanned in that run, not the whole sector.`
            : "Which sectors are leading or lagging the market across the stocks that were scanned."
        }
      />
      <div className="grid gap-5">
        <ResearchDisclaimer />
        {data?.is_synthetic ? <SyntheticDataBanner /> : null}
        <ChartFrame
          title="Relative strength by sector"
          subtitle="Sector return minus the market return over the same period. Above zero means the sector is beating the market."
          isLoading={isLoading}
          error={noRun ? null : error}
          onRetry={() => void refetch()}
          isEmpty={noRun || (!isLoading && chartData.length === 0)}
          emptyTitle="No sector data yet"
          emptyDescription="Sector rotation is built by a research scan. Start a New Research Scan on the Research overview."
          heightClass="h-80"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 6, right: 8, bottom: 0, left: 0 }} barCategoryGap="22%">
              <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="sector"
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
                interval={0}
              />
              <YAxis
                width={40}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickLine={false}
                axisLine={false}
              />
              <ReferenceLine y={0} stroke="var(--muted-foreground)" />
              <Tooltip content={renderTip} cursor={{ fill: "var(--muted)", opacity: 0.4 }} isAnimationActive={false} />
              <Legend verticalAlign="top" height={28} iconType="square" wrapperStyle={{ fontSize: 12 }} />
              <Bar
                dataKey="rs1"
                name="Relative strength 1D"
                fill="var(--chart-1)"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
              <Bar
                dataKey="rs5"
                name="Relative strength 5D"
                fill="var(--warning)"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>

        <DataTable
          columns={columns}
          rows={noRun ? [] : sectors}
          rowKey={(s) => s.sector}
          isLoading={isLoading}
          error={noRun ? null : error}
          onRetry={() => void refetch()}
          emptyTitle="No sector data yet"
          emptyDescription="Start a New Research Scan on the Research overview to build the sector rotation table."
        />
        <p className="text-xs text-muted-foreground">
          Relative strength is the sector return minus the NIFTY 50 return over the same period, breadth is the share of
          its scanned stocks that are advancing, and momentum is a composite score computed by the backend. With few
          stocks per sector these numbers are noisy.
        </p>
      </div>
    </>
  );
}
