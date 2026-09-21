"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Stat, StatRow } from "@/components/dashboard/stat";
import { SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ModeBadge, Pill, SideBadge } from "@/components/trading/badges";
import { Pnl } from "@/components/trading/pnl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/use-debounce";
import { useStrategies } from "@/hooks/use-strategies";
import { useTrades } from "@/hooks/use-trades";
import {
  formatDateTimeShort,
  formatINR,
  formatNumber,
  formatPercent,
  formatPnl,
  formatPrice,
  humanize,
  pnlClass,
} from "@/lib/format";
import type { Trade } from "@/types";

const ALL = "__all__";

const columns: Column<Trade>[] = [
  { key: "exit_time", header: "Exit Time", cell: (t) => formatDateTimeShort(t.exit_time), className: "text-muted-foreground" },
  { key: "entry_time", header: "Entry Time", hideBelow: "lg", cell: (t) => formatDateTimeShort(t.entry_time), className: "text-muted-foreground" },
  { key: "symbol", header: "Symbol", cell: (t) => <span className="font-medium">{t.symbol}</span> },
  { key: "side", header: "Side", cell: (t) => <SideBadge side={t.side} /> },
  { key: "qty", header: "Qty", align: "right", cell: (t) => formatNumber(t.quantity) },
  { key: "entry", header: "Entry", align: "right", hideBelow: "sm", cell: (t) => formatPrice(t.entry_price) },
  { key: "exit", header: "Exit", align: "right", hideBelow: "sm", cell: (t) => formatPrice(t.exit_price) },
  { key: "gross", header: "Gross P&L", align: "right", hideBelow: "md", cell: (t) => <Pnl value={t.gross_pnl} /> },
  { key: "charges", header: "Charges", align: "right", hideBelow: "md", cell: (t) => formatINR(t.charges) },
  { key: "net", header: "Net P&L", align: "right", cell: (t) => <Pnl value={t.net_pnl} /> },
  { key: "reason", header: "Exit Reason", hideBelow: "lg", cell: (t) => <Pill>{humanize(t.exit_reason)}</Pill> },
  {
    key: "strategy",
    header: "Strategy",
    hideBelow: "xl",
    cell: (t) => t.strategy_name ?? <span className="text-muted-foreground">Manual</span>,
  },
  { key: "mode", header: "Mode", hideBelow: "xl", cell: (t) => <ModeBadge mode={t.trading_mode} /> },
];

export function TradesTable() {
  const [strategyId, setStrategyId] = useState<string>(ALL);
  const [symbolInput, setSymbolInput] = useState("");
  const symbol = useDebounce(symbolInput.trim().toUpperCase(), 300);
  const strategies = useStrategies(false);

  const { data, isLoading, error, refetch } = useTrades({
    strategy_id: strategyId === ALL ? undefined : strategyId,
    symbol: symbol || undefined,
    limit: 100,
  });

  const strategyOptions: SelectOption[] = [
    { value: ALL, label: "All strategies" },
    ...(strategies.data ?? []).map((s) => ({ value: s.id, label: s.name })),
  ];

  const trades = data ?? [];
  const net = trades.reduce((s, t) => s + t.net_pnl, 0);
  const gross = trades.reduce((s, t) => s + t.gross_pnl, 0);
  const charges = trades.reduce((s, t) => s + t.charges, 0);
  const wins = trades.filter((t) => t.net_pnl > 0).length;
  const winRate = trades.length > 0 ? (wins / trades.length) * 100 : null;
  const filtered = strategyId !== ALL || symbol !== "";

  return (
    <div className="grid gap-4">
      <StatRow className="sm:grid-cols-4 xl:grid-cols-4">
        <Stat label="Net P&L" loading={isLoading} value={formatPnl(net)} valueClassName={pnlClass(net)} sub={`Gross ${formatPnl(gross)}`} />
        <Stat label="Charges" loading={isLoading} value={formatINR(charges)} sub="Brokerage + statutory" />
        <Stat label="Win Rate" loading={isLoading} value={formatPercent(winRate)} sub={`${wins} wins / ${trades.length - wins} losses`} />
        <Stat label="Trades" loading={isLoading} value={formatNumber(trades.length)} sub={trades.length >= 100 ? "Latest 100 shown" : "In current view"} />
      </StatRow>

      <div className="flex flex-wrap items-center gap-2">
        <div className="w-full sm:w-64">
          <SimpleSelect value={strategyId} onChange={setStrategyId} options={strategyOptions} />
        </div>
        <Input
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          placeholder="Filter by symbol, e.g. INFY"
          aria-label="Filter by symbol"
          className="w-full sm:w-56"
        />
        {filtered ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStrategyId(ALL);
              setSymbolInput("");
            }}
          >
            <X /> Clear filters
          </Button>
        ) : null}
      </div>

      <DataTable
        columns={columns}
        rows={data}
        rowKey={(t) => t.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        skeletonRows={8}
        emptyTitle={filtered ? "No trades match these filters" : "No closed trades yet"}
        emptyDescription="A trade is recorded each time a position is fully exited."
      />
    </div>
  );
}
