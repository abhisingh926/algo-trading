"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FlaskConical, MoreHorizontal, Pencil, Play, Plus, Square, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ModeBadge, StrategyStatusBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { StartStrategyDialog } from "@/components/trading/start-strategy-dialog";
import { StrategySignalsSheet } from "@/components/trading/strategy-signals-sheet";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteStrategy, useStopStrategy, useStrategies } from "@/hooks/use-strategies";
import { formatNumber, formatPercent, humanize } from "@/lib/format";
import type { Strategy } from "@/types";

export function StrategiesTable() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useStrategies();
  const stop = useStopStrategy();
  const remove = useDeleteStrategy();

  // Dialog targets are stored by id so they always show the freshest polled row.
  const [startId, setStartId] = useState<string | null>(null);
  const [stopId, setStopId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const find = (id: string | null) => data?.find((s) => s.id === id) ?? null;
  const toStop = find(stopId);
  const toDelete = find(deleteId);

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
    { key: "type", header: "Type", hideBelow: "md", cell: (s) => humanize(s.strategy_type) },
    {
      key: "status",
      header: "Status",
      cell: (s) => (
        <span title={s.last_error ?? undefined}>
          <StrategyStatusBadge status={s.status} />
        </span>
      ),
    },
    {
      key: "broker",
      header: "Broker",
      hideBelow: "lg",
      cell: (s) => s.broker_name ?? <span className="text-muted-foreground">Default</span>,
    },
    { key: "mode", header: "Trading Mode", hideBelow: "sm", cell: (s) => <ModeBadge mode={s.trading_mode} /> },
    { key: "today", header: "Today's P&L", align: "right", cell: (s) => <Pnl value={s.stats.todays_pnl} /> },
    { key: "total", header: "Total P&L", align: "right", hideBelow: "sm", cell: (s) => <Pnl value={s.stats.total_pnl} /> },
    { key: "trades", header: "Trades", align: "right", hideBelow: "md", cell: (s) => formatNumber(s.stats.trades) },
    {
      key: "win",
      header: "Win Rate",
      align: "right",
      hideBelow: "md",
      cell: (s) => (s.stats.trades > 0 ? formatPercent(s.stats.win_rate) : "—"),
    },
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (s) => {
        const running = s.status === "RUNNING";
        return (
          <div
            className="flex items-center justify-end gap-1"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {running ? (
              <Button variant="outline" size="sm" onClick={() => setStopId(s.id)}>
                <Square /> Stop
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setStartId(s.id)}>
                <Play /> Start
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger
                render={<Button variant="ghost" size="icon-sm" aria-label={`More actions for ${s.name}`} />}
              >
                <MoreHorizontal />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                <DropdownMenuItem disabled={running} onClick={() => router.push(`/strategies/${s.id}/edit`)}>
                  <Pencil /> Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push(`/backtesting?strategy_id=${encodeURIComponent(s.id)}`)}>
                  <FlaskConical /> Backtest
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" disabled={running} onClick={() => setDeleteId(s.id)}>
                  <Trash2 /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        );
      },
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={data}
        rowKey={(s) => s.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        onRowClick={(s) => setDetailId(s.id)}
        emptyTitle="No strategies yet"
        emptyDescription="Create your first strategy, backtest it, then run it in PAPER mode."
        emptyAction={
          <Link href="/strategies/new" className={buttonVariants({ size: "sm" })}>
            <Plus /> Create Strategy
          </Link>
        }
      />

      <StartStrategyDialog
        strategy={find(startId)}
        onOpenChange={(o) => {
          if (!o) setStartId(null);
        }}
      />
      <ConfirmDialog
        open={!!toStop}
        onOpenChange={(o) => {
          if (!o) setStopId(null);
        }}
        title={`Stop "${toStop?.name ?? ""}"?`}
        description="The strategy stops generating signals and orders. Open positions are not closed automatically."
        confirmLabel="Stop strategy"
        pending={stop.isPending}
        onConfirm={() => toStop && stop.mutate(toStop.id, { onSuccess: () => setStopId(null) })}
      />
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => {
          if (!o) setDeleteId(null);
        }}
        title={`Delete "${toDelete?.name ?? ""}"?`}
        description="This permanently removes the strategy configuration. This cannot be undone."
        confirmLabel="Delete strategy"
        destructive
        pending={remove.isPending}
        onConfirm={() => toDelete && remove.mutate(toDelete.id, { onSuccess: () => setDeleteId(null) })}
      />
      <StrategySignalsSheet
        strategy={find(detailId)}
        onOpenChange={(o) => {
          if (!o) setDetailId(null);
        }}
      />
    </>
  );
}
