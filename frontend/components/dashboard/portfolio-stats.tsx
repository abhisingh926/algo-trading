"use client";

import { Stat, StatRow } from "@/components/dashboard/stat";
import { ErrorState } from "@/components/tables/states";
import { useDashboardSummary } from "@/hooks/use-dashboard";
import { formatINR, formatNumber, formatPercent, formatPnl, pnlClass } from "@/lib/format";

export function PortfolioStats() {
  const { data, isLoading, error, refetch } = useDashboardSummary();

  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} className="py-6" />
      </div>
    );
  }

  return (
    <StatRow>
      <Stat label="Capital" loading={isLoading} value={formatINR(data?.capital)} sub={`Total P&L ${formatPnl(data?.total_pnl)}`} />
      <Stat
        label="Available"
        loading={isLoading}
        value={formatINR(data?.available)}
        sub={`Used margin ${formatINR(data?.used_margin)}`}
      />
      <Stat
        label="Today's P&L"
        loading={isLoading}
        value={formatPnl(data?.todays_pnl)}
        valueClassName={pnlClass(data?.todays_pnl)}
        sub={`Realized ${formatPnl(data?.realized_pnl_today)}`}
      />
      <Stat
        label="Open P&L"
        loading={isLoading}
        value={formatPnl(data?.open_pnl)}
        valueClassName={pnlClass(data?.open_pnl)}
        sub={`Open positions: ${formatNumber(data?.open_positions)}`}
      />
      <Stat label="Win Rate" loading={isLoading} value={formatPercent(data?.win_rate)} sub="Closed trades" />
      <Stat
        label="Trades Today"
        loading={isLoading}
        value={formatNumber(data?.trades_today)}
        sub={`Strategies running: ${formatNumber(data?.running_strategies)}`}
      />
    </StatRow>
  );
}
