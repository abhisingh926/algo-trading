"use client";

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartFrame, ChartTooltipBox } from "@/components/charts/chart-frame";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCandles } from "@/hooks/use-research";
import { formatDate, formatDateTimeShort, formatPrice } from "@/lib/format";
import { formatVolume, istClock } from "@/lib/research";
import type { Candle, CandlesQuery, Timeframe } from "@/types";
import type { ResearchReport } from "@/types/research";

interface RangeDef {
  key: string;
  label: string;
  timeframe: Timeframe;
  limit: number;
  /** How far back from the latest candle to show, in days. 0 means the latest session only. */
  days: number;
}
const RANGES: RangeDef[] = [
  { key: "1D", label: "1D", timeframe: "5m", limit: 500, days: 0 },
  { key: "1W", label: "1W", timeframe: "15m", limit: 500, days: 7 },
  { key: "1M", label: "1M", timeframe: "1h", limit: 500, days: 31 },
  { key: "6M", label: "6M", timeframe: "1d", limit: 400, days: 183 },
  { key: "1Y", label: "1Y", timeframe: "1d", limit: 500, days: 366 },
];

interface CandleBar {
  i: number;
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

const IST_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" });

function trim(candles: Candle[], days: number): CandleBar[] {
  const sorted = [...candles].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  if (sorted.length === 0) return [];
  const last = new Date(sorted[sorted.length - 1].timestamp).getTime();
  const istDay = (iso: string | number) => IST_DAY.format(new Date(iso));
  const lastDay = istDay(last);
  const kept =
    days === 0
      ? sorted.filter((c) => istDay(c.timestamp) === lastDay)
      : sorted.filter((c) => new Date(c.timestamp).getTime() >= last - days * 86_400_000);
  return kept.map((c, i) => ({
    i,
    t: new Date(c.timestamp).getTime(),
    o: c.open,
    h: c.high,
    l: c.low,
    c: c.close,
    v: c.volume,
  }));
}

export function PriceChart({ report }: { report: ResearchReport }) {
  const [rangeKey, setRangeKey] = useState("1D");
  const range = RANGES.find((r) => r.key === rangeKey) ?? RANGES[0];
  const query: CandlesQuery = useMemo(
    () => ({
      symbol: report.symbol,
      exchange: report.overview.exchange,
      timeframe: range.timeframe,
      limit: range.limit,
    }),
    [report.symbol, report.overview.exchange, range],
  );
  const { data, isLoading, error, refetch } = useCandles(query);
  const bars = useMemo(() => trim(data ?? [], range.days), [data, range.days]);
  const intraday = range.days <= 31 && range.timeframe !== "1d";
  const label = (t: number) =>
    intraday
      ? range.days === 0
        ? istClock(new Date(t).toISOString()).replace(" IST", "")
        : formatDateTimeShort(new Date(t)).slice(0, 6)
      : formatDate(new Date(t)).slice(0, 6);
  const vwap = range.key === "1D" ? report.technical.levels.vwap : null;
  const prevClose = range.key === "1D" ? report.technical.levels.prev_day_close : null;

  const renderTip = ({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: CandleBar }> }) => {
    const b = payload?.[0]?.payload;
    if (!active || !b) return null;
    return (
      <ChartTooltipBox
        title={`${formatDateTimeShort(new Date(b.t))} IST`}
        rows={[
          { label: "Open", value: formatPrice(b.o) },
          { label: "High", value: formatPrice(b.h) },
          { label: "Low", value: formatPrice(b.l) },
          { label: "Close", value: formatPrice(b.c) },
          { label: "Volume", value: formatVolume(b.v) },
        ]}
      />
    );
  };

  const xAxis = (hide: boolean) => (
    <XAxis
      dataKey="i"
      type="number"
      domain={["dataMin", "dataMax"]}
      tickFormatter={(i: number) => (bars[i] ? label(bars[i].t) : "")}
      tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
      tickLine={false}
      axisLine={{ stroke: "var(--border)" }}
      minTickGap={48}
      hide={hide}
    />
  );

  return (
    <section aria-label="Price chart" className="grid gap-2">
      <ChartFrame
        title={`${report.symbol} price`}
        subtitle={`Close price, ${range.timeframe} candles. Times in IST.`}
        actions={
          <Tabs value={rangeKey} onValueChange={(v) => setRangeKey(String(v))}>
            <TabsList>
              {RANGES.map((r) => (
                <TabsTrigger key={r.key} value={r.key}>
                  {r.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        }
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        isEmpty={bars.length === 0}
        emptyTitle="No candles stored for this range"
        emptyDescription="Price history is limited to what the backend has stored for this symbol."
        heightClass="h-72"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={bars} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.25} />
                <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
            {xAxis(false)}
            <YAxis
              width={60}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => formatPrice(v)}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              tickLine={false}
              axisLine={false}
            />
            {vwap !== null ? (
              <ReferenceLine
                y={vwap}
                stroke="var(--warning)"
                strokeDasharray="4 4"
                label={{ value: "VWAP", fill: "var(--warning)", fontSize: 11, position: "insideTopRight" }}
              />
            ) : null}
            {prevClose !== null ? (
              <ReferenceLine
                y={prevClose}
                stroke="var(--muted-foreground)"
                strokeDasharray="2 4"
                label={{
                  value: "Prev close",
                  fill: "var(--muted-foreground)",
                  fontSize: 11,
                  position: "insideBottomRight",
                }}
              />
            ) : null}
            <Tooltip
              content={renderTip}
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="c"
              stroke="var(--chart-1)"
              strokeWidth={2}
              fill="url(#priceFill)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartFrame>
      {bars.length > 0 ? (
        <div className="h-20 rounded-lg border bg-card p-2" aria-label="Volume">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bars} margin={{ top: 2, right: 8, bottom: 0, left: 0 }}>
              {xAxis(true)}
              <YAxis
                width={60}
                tickFormatter={(v: number) => formatVolume(v)}
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickLine={false}
                axisLine={false}
                tickCount={2}
              />
              <Tooltip content={renderTip} cursor={{ fill: "var(--muted)", opacity: 0.4 }} isAnimationActive={false} />
              <Bar dataKey="v" fill="var(--muted-foreground)" fillOpacity={0.5} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}
      <p className="text-xs text-muted-foreground">
        Price history is limited to the candles stored on the backend and, with the simulated feed, may be synthetic
        test data. Longer ranges use daily candles, so they show fewer points than the range suggests.
        {report.is_synthetic ? " This report was built on synthetic data." : ""}
      </p>
    </section>
  );
}
