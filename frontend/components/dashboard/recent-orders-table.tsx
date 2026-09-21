"use client";

import { DataTable, type Column } from "@/components/tables/data-table";
import { OrderStatusBadge, SideBadge } from "@/components/trading/badges";
import { useOrders } from "@/hooks/use-orders";
import { formatDateTimeShort, formatNumber, formatPrice } from "@/lib/format";
import type { Order, OrdersQuery } from "@/types";

const columns: Column<Order>[] = [
  { key: "time", header: "Time", cell: (o) => formatDateTimeShort(o.created_at), className: "text-muted-foreground" },
  { key: "symbol", header: "Symbol", cell: (o) => <span className="font-medium">{o.symbol}</span> },
  { key: "side", header: "Side", cell: (o) => <SideBadge side={o.side} /> },
  { key: "qty", header: "Qty", align: "right", cell: (o) => formatNumber(o.quantity) },
  {
    key: "price",
    header: "Price",
    align: "right",
    cell: (o) => (o.average_fill_price ?? o.price) !== null ? formatPrice(o.average_fill_price ?? o.price) : "MKT",
  },
  { key: "status", header: "Status", cell: (o) => <OrderStatusBadge status={o.status} /> },
];

const QUERY: OrdersQuery = { status_group: "all", limit: 10 };

export function RecentOrdersTable() {
  const { data, isLoading, error, refetch } = useOrders(QUERY);
  return (
    <DataTable
      columns={columns}
      rows={data}
      rowKey={(o) => o.id}
      isLoading={isLoading}
      error={error}
      onRetry={() => void refetch()}
      maxHeightClass="max-h-96"
      emptyTitle="No orders yet"
      emptyDescription="Orders placed by strategies or manually will appear here."
    />
  );
}
