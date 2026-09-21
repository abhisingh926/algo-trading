"use client";

import { DataTable, type Column } from "@/components/tables/data-table";
import { SideBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { usePositions } from "@/hooks/use-positions";
import { formatNumber, formatPrice } from "@/lib/format";
import type { Position } from "@/types";

const columns: Column<Position>[] = [
  {
    key: "symbol",
    header: "Symbol",
    cell: (p) => (
      <span className="flex items-center gap-2 font-medium">
        {p.symbol} <SideBadge side={p.side} />
      </span>
    ),
  },
  { key: "qty", header: "Qty", align: "right", cell: (p) => formatNumber(p.quantity) },
  { key: "entry", header: "Entry", align: "right", cell: (p) => formatPrice(p.average_entry_price) },
  { key: "ltp", header: "LTP", align: "right", cell: (p) => formatPrice(p.last_price) },
  { key: "pnl", header: "P&L", align: "right", cell: (p) => <Pnl value={p.unrealized_pnl} /> },
];

export function OpenPositionsTable() {
  const { data, isLoading, error, refetch } = usePositions("open");
  return (
    <DataTable
      columns={columns}
      rows={data}
      rowKey={(p) => p.id}
      isLoading={isLoading}
      error={error}
      onRetry={() => void refetch()}
      skeletonRows={3}
      maxHeightClass="max-h-72"
      emptyTitle="No open positions"
      emptyDescription="Positions opened by strategies or manual orders show up here."
    />
  );
}
