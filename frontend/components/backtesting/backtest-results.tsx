"use client";

import { useMemo } from "react";
import { AlertTriangle, Info } from "lucide-react";
import { ChartFrame } from "@/components/charts/chart-frame";
import { TimeSeriesChart } from "@/components/charts/time-series-chart";
import { TradeDistributionChart } from "@/components/charts/trade-distribution-chart";
import { Stat, StatRow } from "@/components/dashboard/stat";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ErrorState } from "@/components/tables/states";
import { BacktestStatusBadge, SideBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktestReport } from "@/hooks/use-backtests";
import {
  formatDate,
  formatDateTimeShort,
  formatINR,
  formatINRCompact,
  formatNumber,
  formatPercent,
  formatPnl,
  formatPrice,
  humanize,
  pnlClass,
} from "@/lib/format";
import type { BacktestTrade } from "@/types";

const tradeColumns: Column<BacktestTrade>[] = [
  { key: "entry_time", header: "Entry Time", cell: (t) => formatDateTimeShort(t.entry_time), className: "text-muted-foreground" },
  { key: "exit_time", header: "Exit Time", cell: (t) => formatDateTimeShort(t.exit_time), className: "text-muted-foreground" },
  { key: "symbol", header: "Symbol", cell: (t) => <span className="font-medium">{t.symbol}</span> },
  { key: "side", header: "Side", cell: (t) => <SideBadge side={t.side} /> },
  { key: "entry", header: "Entry", align: "right", cell: (t) => formatPrice(t.entry_price) },
  { key: "exit", header: "Exit", align: "right", cell: (t) => formatPrice(t.exit_price) },
  { key: "qty", header: "Quantity", align: "right", cell: (t) => formatNumber(t.quantity) },
  { key: "charges", header: "Charges", align: "right", hideBelow: "lg", cell: (t) => formatINR(t.charges) },
  { key: "reason", header: "Exit Reason", hideBelow: "lg", cell: (t) => humanize(t.exit_reason) },
  { key: "pnl", header: "P&L", align: "right", cell: (t) => <Pnl value={t.net_pnl} /> },
];

export function BacktestResults({ backtestId }: { backtestId: string }) {
  const { data, isLoading, error, refetch } = useBacktestReport(backtestId);

  const equity = useMemo(
    () => (data?.equity_curve ?? []).map((p) => ({ t: new Date(p.timestamp).getTime(), value: p.equity })),
    [data],
  );
  const drawdown = useMemo(
    // Normalised to <= 0 so the curve always hangs below the zero line.
    () => (data?.equity_curve ?? []).map((p) => ({ t: new Date(p.timestamp).getTime(), value: -Math.abs(p.drawdown_pct) })),
    [data],
  );
  const pnls = useMemo(() => (data?.trades ?? []).map((t) => t.net_pnl), [data]);

  if (isLoading) {
    return (
      <div className="grid gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error ?? new Error("Backtest not found")} onRetry={() => void refetch()} />
      </div>
    );
  }

  const { backtest: bt, trades } = data;
  const m = bt.metrics;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h2 className="text-base font-semibold">{bt.name}</h2>
        <BacktestStatusBadge status={bt.status} />
        <p className="basis-full text-xs text-muted-foreground">
          {humanize(bt.strategy_type)} · {bt.symbol} ({bt.exchange}) · {bt.timeframe} · {formatDate(bt.start_date)} to{" "}
          {formatDate(bt.end_date)} · Initial capital {formatINR(bt.initial_capital, { whole: true })}
        </p>
      </div>

      {bt.status === "FAILED" ? (
        <p role="alert" className="flex gap-2 rounded-md border border-loss/40 bg-loss/10 p-3 text-sm text-loss">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>
            <strong>Backtest failed.</strong> {bt.error_message ?? "No error message was provided."}
          </span>
        </p>
      ) : null}

      {m?.data_source === "simulated" ? (
        <p className="flex gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
          <Info className="mt-0.5 size-4 shrink-0" />
          <span>
            <strong>Synthetic data.</strong> This backtest ran on simulated candles, not real market history.
            Results do not reflect real market behaviour.
          </span>
        </p>
      ) : null}

      {m ? (
        <>
          <StatRow className="sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-5">
            <Stat label="Total Return" value={formatPercent(m.total_return_pct, 2, true)} valueClassName={pnlClass(m.total_return_pct)} sub={`Final ${formatINR(m.final_capital, { whole: true })}`} />
            <Stat label="Net P&L" value={formatPnl(m.net_pnl)} valueClassName={pnlClass(m.net_pnl)} sub={`Gross +${formatINR(m.gross_profit, { whole: true })} / -${formatINR(Math.abs(m.gross_loss), { whole: true })}`} />
            <Stat label="Win Rate" value={formatPercent(m.win_rate)} sub={`${m.winning_trades} W / ${m.losing_trades} L`} />
            <Stat label="Profit Factor" value={m.profit_factor === null ? "—" : m.profit_factor.toFixed(2)} sub="Gross profit ÷ gross loss" />
            <Stat label="Max Drawdown" value={formatPercent(-Math.abs(m.max_drawdown_pct), 2)} valueClassName="text-loss" sub={formatINR(Math.abs(m.max_drawdown), { whole: true })} />
            <Stat label="Total Trades" value={formatNumber(m.total_trades)} sub={`${formatNumber(m.candles_processed)} candles`} />
            <Stat label="Average Trade" value={formatPnl(m.average_trade)} valueClassName={pnlClass(m.average_trade)} sub={`Best ${formatPnl(m.largest_win)} · Worst ${formatPnl(m.largest_loss)}`} />
            <Stat label="Sharpe Ratio" value={m.sharpe_ratio === null ? "—" : m.sharpe_ratio.toFixed(2)} />
            <Stat label="Charges" value={formatINR(m.total_charges)} sub={`Slippage ${formatINR(m.total_slippage)}`} />
            <Stat label="Data Source" value={<span className="capitalize">{m.data_source}</span>} />
          </StatRow>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame
              title="Equity Curve"
              subtitle="Account equity over the test period"
              className="xl:col-span-2"
              isEmpty={equity.length === 0}
              emptyTitle="No equity points recorded"
              heightClass="h-72"
            >
              <TimeSeriesChart
                data={equity}
                label="Equity"
                formatValue={(v) => formatINR(v)}
                formatAxis={formatINRCompact}
                baseline={bt.initial_capital}
              />
            </ChartFrame>
            <ChartFrame
              title="Drawdown"
              subtitle="Percent below the running equity peak"
              isEmpty={drawdown.length === 0}
              emptyTitle="No drawdown data"
            >
              <TimeSeriesChart
                data={drawdown}
                label="Drawdown"
                color="var(--loss)"
                formatValue={(v) => formatPercent(v, 2)}
                includeZero
              />
            </ChartFrame>
            <ChartFrame
              title="Trade Distribution"
              subtitle="Number of trades by net P&L per trade"
              isEmpty={pnls.length === 0}
              emptyTitle="No trades were taken"
            >
              <TradeDistributionChart values={pnls} />
            </ChartFrame>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold">Trades ({trades.length})</h3>
            <DataTable
              columns={tradeColumns}
              rows={trades}
              rowKey={(t) => t.id}
              isLoading={false}
              error={null}
              maxHeightClass="max-h-[32rem]"
              emptyTitle="No trades were taken"
              emptyDescription="The strategy produced no entries in this period. Try a longer date range or different parameters."
            />
          </div>
        </>
      ) : bt.status !== "FAILED" ? (
        <p className="rounded-lg border bg-card p-6 text-center text-sm text-muted-foreground">
          This backtest is {bt.status.toLowerCase()} and has no metrics yet.
        </p>
      ) : null}
    </div>
  );
}
