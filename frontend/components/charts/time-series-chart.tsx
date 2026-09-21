"use client";

import { useId } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartTooltipBox } from "@/components/charts/chart-frame";
import { formatDate, formatDateTimeShort, formatTime } from "@/lib/format";

export interface SeriesPoint {
  /** epoch milliseconds */
  t: number;
  value: number;
}

interface TimeSeriesChartProps {
  data: SeriesPoint[];
  label: string;
  /** CSS colour, usually a theme variable such as var(--chart-1). */
  color?: string;
  formatValue: (v: number) => string;
  formatAxis?: (v: number) => string;
  /** Draw a baseline (e.g. starting capital or zero). */
  baseline?: number;
  /** Show only dates (daily data) rather than date + time. */
  dateOnly?: boolean;
  /** Anchor the fill to the top (for drawdown, where values are <= 0). */
  includeZero?: boolean;
}

interface TooltipRenderProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: SeriesPoint }>;
}

export function TimeSeriesChart({
  data,
  label,
  color = "var(--chart-1)",
  formatValue,
  formatAxis,
  baseline,
  dateOnly,
  includeZero,
}: TimeSeriesChartProps) {
  const gradientId = useId().replace(/:/g, "");
  const fmtTime = (t: number) => (dateOnly ? formatDate(new Date(t)) : formatDateTimeShort(new Date(t)));

  // Short ranges (intraday equity) need clock times on the X axis, and a compact Y formatter would
  // collapse every tick to the same label ("₹5L"), so fall back to the precise formatter there.
  const first = data[0];
  const last = data[data.length - 1];
  const intraday = !dateOnly && first !== undefined && last !== undefined && last.t - first.t < 36 * 3600 * 1000;
  const values = data.map((d) => d.value);
  const lo = values.length ? Math.min(...values) : 0;
  const hi = values.length ? Math.max(...values) : 0;
  const compactCollides = formatAxis !== undefined && lo !== hi && formatAxis(lo) === formatAxis(hi);
  const yFormatter = formatAxis && !compactCollides ? formatAxis : formatValue;
  const xFormatter = (t: number) =>
    intraday ? formatTime(new Date(t)).slice(0, 5) : formatDate(new Date(t)).slice(0, 6);

  const renderTooltip = ({ active, payload }: TooltipRenderProps) => {
    const p = payload?.[0]?.payload;
    if (!active || !p) return null;
    return <ChartTooltipBox title={`${fmtTime(p.t)} IST`} rows={[{ label, value: formatValue(p.value) }]} />;
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={includeZero ? 0.05 : 0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={includeZero ? 0.25 : 0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={xFormatter}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          minTickGap={48}
        />
        <YAxis
          width={compactCollides ? 96 : 64}
          domain={includeZero ? ["auto", 0] : ["auto", "auto"]}
          tickFormatter={yFormatter}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
        />
        {baseline !== undefined ? (
          <ReferenceLine y={baseline} stroke="var(--muted-foreground)" strokeDasharray="4 4" strokeOpacity={0.6} />
        ) : null}
        <Tooltip
          content={renderTooltip}
          cursor={{ stroke: "var(--muted-foreground)", strokeWidth: 1, strokeDasharray: "3 3" }}
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="value"
          name={label}
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={false}
          activeDot={{ r: 4, stroke: "var(--card)", strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
