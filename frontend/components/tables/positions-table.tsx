"use client";

import { useState } from "react";
import { Pencil, X } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ModeBadge, SideBadge } from "@/components/trading/badges";
import { EditPositionDialog } from "@/components/trading/edit-position-dialog";
import { Pnl } from "@/components/trading/pnl";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useClosePosition, usePositions } from "@/hooks/use-positions";
import { formatDateTimeShort, formatNumber, formatPrice } from "@/lib/format";
import type { Position } from "@/types";

export function PositionsTable() {
  const [view, setView] = useState<"open" | "closed">("open");
  const { data, isLoading, error, refetch } = usePositions(view);
  const close = useClosePosition();
  const [editId, setEditId] = useState<string | null>(null);
  const [toClose, setToClose] = useState<Position | null>(null);
  const isOpen = view === "open";

  const shared: Column<Position>[] = [
    {
      key: "symbol",
      header: "Symbol",
      cell: (p) => (
        <div>
          <span className="font-medium">{p.symbol}</span>{" "}
          <span className="text-xs text-muted-foreground">{p.exchange}</span>
        </div>
      ),
    },
    { key: "side", header: "Side", cell: (p) => <SideBadge side={p.side} /> },
    { key: "qty", header: "Quantity", align: "right", cell: (p) => formatNumber(p.quantity) },
    { key: "entry", header: "Entry Price", align: "right", cell: (p) => formatPrice(p.average_entry_price) },
  ];
  const tail: Column<Position>[] = [
    {
      key: "strategy",
      header: "Strategy",
      hideBelow: "lg",
      cell: (p) => p.strategy_name ?? <span className="text-muted-foreground">Manual</span>,
    },
    { key: "mode", header: "Mode", hideBelow: "xl", cell: (p) => <ModeBadge mode={p.trading_mode} /> },
  ];

  const openColumns: Column<Position>[] = [
    ...shared,
    { key: "ltp", header: "Current Price", align: "right", cell: (p) => formatPrice(p.last_price) },
    { key: "upnl", header: "Unrealized P&L", align: "right", cell: (p) => <Pnl value={p.unrealized_pnl} /> },
    { key: "sl", header: "Stop Loss", align: "right", hideBelow: "md", cell: (p) => formatPrice(p.stop_loss) },
    { key: "target", header: "Target", align: "right", hideBelow: "md", cell: (p) => formatPrice(p.target) },
    ...tail,
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (p) => (
        <div className="flex justify-end gap-1">
          <Button variant="outline" size="xs" onClick={() => setEditId(p.id)}>
            <Pencil /> SL / Target
          </Button>
          <Button variant="destructive" size="xs" onClick={() => setToClose(p)}>
            <X /> Close
          </Button>
        </div>
      ),
    },
  ];
  const closedColumns: Column<Position>[] = [
    ...shared,
    { key: "rpnl", header: "Realized P&L", align: "right", cell: (p) => <Pnl value={p.realized_pnl} /> },
    { key: "opened", header: "Opened", hideBelow: "md", cell: (p) => formatDateTimeShort(p.opened_at) },
    { key: "closed", header: "Closed", hideBelow: "sm", cell: (p) => formatDateTimeShort(p.closed_at) },
    ...tail,
  ];

  const totalUnrealized = (data ?? []).reduce((s, p) => s + p.unrealized_pnl, 0);
  const totalRealized = (data ?? []).reduce((s, p) => s + p.realized_pnl, 0);

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Tabs value={view} onValueChange={(v) => setView(v === "closed" ? "closed" : "open")}>
          <TabsList>
            <TabsTrigger value="open">Open</TabsTrigger>
            <TabsTrigger value="closed">Closed</TabsTrigger>
          </TabsList>
        </Tabs>
        {data && data.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            {data.length} positions · {isOpen ? "Unrealized" : "Realized"} P&amp;L{" "}
            <Pnl value={isOpen ? totalUnrealized : totalRealized} />
          </p>
        ) : null}
      </div>
      <DataTable
        key={view}
        columns={isOpen ? openColumns : closedColumns}
        rows={data}
        rowKey={(p) => p.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        emptyTitle={isOpen ? "No open positions" : "No closed positions"}
        emptyDescription={
          isOpen
            ? "Positions opened by strategies or manual orders show up here with live P&L."
            : "Positions move here once they are fully exited."
        }
      />
      <EditPositionDialog
        position={data?.find((p) => p.id === editId) ?? null}
        onOpenChange={(o) => {
          if (!o) setEditId(null);
        }}
      />
      <ConfirmDialog
        open={!!toClose}
        onOpenChange={(o) => {
          if (!o) setToClose(null);
        }}
        title={`Close ${toClose?.symbol ?? ""} position?`}
        description={
          toClose
            ? `A MARKET ${toClose.side === "LONG" ? "SELL" : "BUY"} order for ${toClose.quantity} × ${toClose.symbol} will be placed in ${toClose.trading_mode} mode to exit the position at the current price.`
            : undefined
        }
        confirmLabel="Close position"
        cancelLabel="Keep position"
        destructive
        pending={close.isPending}
        onConfirm={() => toClose && close.mutate(toClose.id, { onSuccess: () => setToClose(null) })}
      >
        {toClose ? (
          <p className="text-sm">
            Unrealized P&amp;L: <Pnl value={toClose.unrealized_pnl} />
          </p>
        ) : null}
      </ConfirmDialog>
    </>
  );
}
