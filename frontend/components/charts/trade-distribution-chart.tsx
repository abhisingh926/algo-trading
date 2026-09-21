"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltipBox } from "@/components/charts/chart-frame";
import { formatINR, formatINRCompact } from "@/lib/format";

interface Bin {
  from: number;
  to: number;
  mid: number;
  count: number;
  label: string;
}

/** Bins trade net P&L into a histogram with "nice" bin edges aligned on zero. */
export function buildPnlBins(values: number[], targetBins = 16): Bin[] {
  if (values.length === 0) return [];
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min || Math.abs(max) || 1;
  const raw = span / targetBins;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) ?? 10) * mag;
  const start = Math.floor(min / step) * step;
  const count = Math.max(1, Math.ceil((max - start) / step) || 1);
  const bins: Bin[] = Array.from({ length: count }, (_, i) => {
    const from = start + i * step;
    const to = from + step;
    return { from, to, mid: (from + to) / 2, count: 0, label: formatINRCompact(from) };
  });
  for (const v of values) {
    const idx = Math.min(bins.length - 1, Math.max(0, Math.floor((v - start) / step)));
    bins[idx].count += 1;
  }
  return bins;
}

interface TooltipRenderProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: Bin }>;
}

function renderTooltip({ active, payload }: TooltipRenderProps) {
  const b = payload?.[0]?.payload;
  if (!active || !b) return null;
  return (
    <ChartTooltipBox
      title={`${formatINR(b.from, { whole: true })} to ${formatINR(b.to, { whole: true })}`}
      rows={[{ label: "Trades", value: String(b.count) }]}
    />
  );
}

export function TradeDistributionChart({ values }: { values: number[] }) {
  const bins = useMemo(() => buildPnlBins(values), [values]);
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={bins} margin={{ top: 6, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
        <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          minTickGap={24}
        />
        <YAxis
          width={36}
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={renderTooltip} cursor={{ fill: "var(--muted)", opacity: 0.5 }} isAnimationActive={false} />
        <Bar dataKey="count" name="Trades" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {bins.map((b) => (
            <Cell key={b.from} fill={b.mid >= 0 ? "var(--profit)" : "var(--loss)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
