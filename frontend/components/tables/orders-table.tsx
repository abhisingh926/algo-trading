"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ModeBadge, OrderStatusBadge, SideBadge } from "@/components/trading/badges";
import { OrderDetailDialog } from "@/components/trading/order-detail-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCancelOrder, useOrders } from "@/hooks/use-orders";
import { formatDateTimeShort, formatNumber, formatPrice, humanize } from "@/lib/format";
import { OPEN_ORDER_STATUSES, type Order, type OrderStatusGroup } from "@/types";

const GROUPS: { value: OrderStatusGroup; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "filled", label: "Filled" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
];

const EMPTY_TEXT: Record<OrderStatusGroup, string> = {
  all: "No orders yet",
  open: "No open orders",
  filled: "No filled orders",
  rejected: "No rejected or failed orders",
  cancelled: "No cancelled or expired orders",
};

export function OrdersTable() {
  const [group, setGroup] = useState<OrderStatusGroup>("all");
  const { data, isLoading, error, refetch } = useOrders({ status_group: group, limit: 100 });
  const cancel = useCancelOrder();
  const [detailId, setDetailId] = useState<string | null>(null);
  const [toCancel, setToCancel] = useState<Order | null>(null);

  const columns: Column<Order>[] = [
    { key: "time", header: "Time", cell: (o) => formatDateTimeShort(o.created_at), className: "text-muted-foreground" },
    { key: "symbol", header: "Symbol", cell: (o) => <span className="font-medium">{o.symbol}</span> },
    { key: "side", header: "Side", cell: (o) => <SideBadge side={o.side} /> },
    { key: "type", header: "Type", hideBelow: "md", cell: (o) => o.order_type },
    { key: "qty", header: "Qty", align: "right", cell: (o) => formatNumber(o.quantity) },
    { key: "filled", header: "Filled", align: "right", hideBelow: "md", cell: (o) => formatNumber(o.filled_quantity) },
    {
      key: "price",
      header: "Price",
      align: "right",
      hideBelow: "sm",
      cell: (o) => (o.price !== null ? formatPrice(o.price) : o.trigger_price !== null ? `T ${formatPrice(o.trigger_price)}` : "MKT"),
    },
    { key: "avg", header: "Avg Fill", align: "right", hideBelow: "lg", cell: (o) => formatPrice(o.average_fill_price) },
    {
      key: "status",
      header: "Status",
      cell: (o) => (
        <span title={o.status_message ?? undefined}>
          <OrderStatusBadge status={o.status} />
        </span>
      ),
    },
    { key: "source", header: "Source", hideBelow: "lg", cell: (o) => humanize(o.source) },
    {
      key: "strategy",
      header: "Strategy",
      hideBelow: "xl",
      cell: (o) => o.strategy_name ?? <span className="text-muted-foreground">—</span>,
    },
    { key: "mode", header: "Mode", hideBelow: "xl", cell: (o) => <ModeBadge mode={o.trading_mode} /> },
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (o) =>
        OPEN_ORDER_STATUSES.includes(o.status) ? (
          <Button
            variant="destructive"
            size="xs"
            onClick={(e) => {
              e.stopPropagation();
              setToCancel(o);
            }}
          >
            <X /> Cancel
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <Tabs value={group} onValueChange={(v) => setGroup(v as OrderStatusGroup)} className="mb-3">
        <TabsList>
          {GROUPS.map((g) => (
            <TabsTrigger key={g.value} value={g.value}>
              {g.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <DataTable
        columns={columns}
        rows={data}
        rowKey={(o) => o.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        onRowClick={(o) => setDetailId(o.id)}
        skeletonRows={8}
        emptyTitle={EMPTY_TEXT[group]}
        emptyDescription="Orders from strategies, manual entry, risk exits and the kill switch are listed here."
      />
      <OrderDetailDialog
        orderId={detailId}
        onOpenChange={(o) => {
          if (!o) setDetailId(null);
        }}
      />
      <ConfirmDialog
        open={!!toCancel}
        onOpenChange={(o) => {
          if (!o) setToCancel(null);
        }}
        title="Cancel this order?"
        description={
          toCancel
            ? `${toCancel.side} ${toCancel.quantity} × ${toCancel.symbol} (${toCancel.order_type}). Any quantity already filled is not affected.`
            : undefined
        }
        confirmLabel="Cancel order"
        cancelLabel="Keep order"
        destructive
        pending={cancel.isPending}
        onConfirm={() => toCancel && cancel.mutate(toCancel.id, { onSuccess: () => setToCancel(null) })}
      />
    </>
  );
}
