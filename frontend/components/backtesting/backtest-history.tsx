"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { DataTable, type Column } from "@/components/tables/data-table";
import { BacktestStatusBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { Button } from "@/components/ui/button";
import { useBacktests, useDeleteBacktest } from "@/hooks/use-backtests";
import { formatDate, formatDateTimeShort, formatNumber, formatPercent, pnlClass } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Backtest } from "@/types";

interface BacktestHistoryProps {
  selectedId: string | null;
  onOpen: (id: string) => void;
  onDeleted: (id: string) => void;
}

export function BacktestHistory({ selectedId, onOpen, onDeleted }: BacktestHistoryProps) {
  const { data, isLoading, error, refetch } = useBacktests(50);
  const remove = useDeleteBacktest();
  const [toDelete, setToDelete] = useState<Backtest | null>(null);

  const columns: Column<Backtest>[] = [
    { key: "created", header: "Run At", cell: (b) => formatDateTimeShort(b.created_at), className: "text-muted-foreground" },
    {
      key: "name",
      header: "Name",
      cell: (b) => (
        <span className="block max-w-72 truncate font-medium" title={b.error_message ?? b.name}>
          {b.name}
        </span>
      ),
    },
    { key: "symbol", header: "Symbol", hideBelow: "sm", cell: (b) => `${b.symbol} · ${b.timeframe}` },
    {
      key: "period",
      header: "Period",
      hideBelow: "lg",
      cell: (b) => `${formatDate(b.start_date)} to ${formatDate(b.end_date)}`,
    },
    { key: "status", header: "Status", cell: (b) => <BacktestStatusBadge status={b.status} /> },
    {
      key: "return",
      header: "Return",
      align: "right",
      cell: (b) => (
        <span className={cn("font-medium", pnlClass(b.metrics?.total_return_pct))}>
          {formatPercent(b.metrics?.total_return_pct, 2, true)}
        </span>
      ),
    },
    { key: "pnl", header: "Net P&L", align: "right", hideBelow: "md", cell: (b) => <Pnl value={b.metrics?.net_pnl} /> },
    { key: "trades", header: "Trades", align: "right", hideBelow: "md", cell: (b) => formatNumber(b.metrics?.total_trades) },
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (b) => (
        <div className="flex justify-end gap-1">
          <Button variant="outline" size="xs" onClick={(e) => { e.stopPropagation(); onOpen(b.id); }}>
            Open
          </Button>
          <Button
            variant="destructive"
            size="icon-xs"
            aria-label={`Delete backtest ${b.name}`}
            onClick={(e) => {
              e.stopPropagation();
              setToDelete(b);
            }}
          >
            <Trash2 />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={data}
        rowKey={(b) => b.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        onRowClick={(b) => onOpen(b.id)}
        rowClassName={(b) => (b.id === selectedId ? "bg-muted/60" : undefined)}
        maxHeightClass="max-h-96"
        emptyTitle="No backtests yet"
        emptyDescription="Run a backtest above and it will be saved here."
      />
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => {
          if (!o) setToDelete(null);
        }}
        title="Delete this backtest?"
        description={toDelete ? `"${toDelete.name}" and its trades and equity curve will be permanently removed.` : undefined}
        confirmLabel="Delete backtest"
        destructive
        pending={remove.isPending}
        onConfirm={() =>
          toDelete &&
          remove.mutate(toDelete.id, {
            onSuccess: () => {
              onDeleted(toDelete.id);
              setToDelete(null);
            },
          })
        }
      />
    </>
  );
}
