"use client";

import Link from "next/link";
import { DataTable, type Column } from "@/components/tables/data-table";
import { StrategyStatusBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { buttonVariants } from "@/components/ui/button";
import { useStrategies } from "@/hooks/use-strategies";
import { formatNumber } from "@/lib/format";
import type { Strategy } from "@/types";

const columns: Column<Strategy>[] = [
  {
    key: "name",
    header: "Name",
    cell: (s) => (
      <div className="min-w-0">
        <p className="truncate font-medium">{s.name}</p>
        <p className="text-xs text-muted-foreground">
          {s.symbol} · {s.timeframe}
        </p>
      </div>
    ),
  },
  { key: "status", header: "Status", cell: (s) => <StrategyStatusBadge status={s.status} /> },
  { key: "pnl", header: "P&L", align: "right", cell: (s) => <Pnl value={s.stats.todays_pnl} /> },
  { key: "trades", header: "Trades", align: "right", cell: (s) => formatNumber(s.stats.trades) },
];

export function ActiveStrategiesTable() {
  const { data, isLoading, error, refetch } = useStrategies();
  // Running (and errored) strategies first; stopped ones are not "active".
  const rows = data?.filter((s) => s.status !== "STOPPED");
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(s) => s.id}
      isLoading={isLoading}
      error={error}
      onRetry={() => void refetch()}
      skeletonRows={3}
      maxHeightClass="max-h-72"
      emptyTitle="No active strategies"
      emptyDescription={
        data && data.length > 0
          ? `${data.length} strategies configured, none running.`
          : "Create a strategy and start it in PAPER mode."
      }
      emptyAction={
        <Link href="/strategies" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Go to strategies
        </Link>
      }
    />
  );
}
