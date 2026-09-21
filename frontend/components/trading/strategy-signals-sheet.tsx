"use client";

import { DataTable, type Column } from "@/components/tables/data-table";
import { ModeBadge, SideBadge, SignalStatusBadge, StrategyStatusBadge } from "@/components/trading/badges";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useStrategySignals } from "@/hooks/use-strategies";
import { formatDateTime, formatDateTimeShort, formatFraction, formatINR, formatPrice } from "@/lib/format";
import type { Signal, Strategy } from "@/types";

const columns: Column<Signal>[] = [
  { key: "time", header: "Time", cell: (s) => formatDateTimeShort(s.created_at), className: "text-muted-foreground" },
  { key: "signal", header: "Signal", cell: (s) => <SideBadge side={s.signal_type} /> },
  { key: "price", header: "Price", align: "right", cell: (s) => formatPrice(s.price) },
  { key: "status", header: "Status", cell: (s) => <SignalStatusBadge status={s.status} /> },
  {
    key: "reason",
    header: "Reason",
    cell: (s) => (
      <span className="block max-w-64 truncate text-xs text-muted-foreground" title={s.status_reason ?? s.reason}>
        {s.status_reason ?? s.reason}
      </span>
    ),
  },
];

export function StrategySignalsSheet({
  strategy,
  onOpenChange,
}: {
  strategy: Strategy | null;
  onOpenChange: (open: boolean) => void;
}) {
  const signals = useStrategySignals(strategy?.id ?? null, 50);
  return (
    <Sheet open={!!strategy} onOpenChange={(o) => onOpenChange(o)}>
      <SheetContent className="w-full gap-0 overflow-y-auto data-[side=right]:sm:max-w-2xl">
        {strategy ? (
          <>
            <SheetHeader>
              <SheetTitle className="flex flex-wrap items-center gap-2">
                {strategy.name} <StrategyStatusBadge status={strategy.status} />
                <ModeBadge mode={strategy.trading_mode} />
              </SheetTitle>
              <SheetDescription>
                {strategy.strategy_type.replace(/_/g, " ")} on {strategy.symbol} ({strategy.exchange}) ·{" "}
                {strategy.timeframe}
              </SheetDescription>
            </SheetHeader>
            <div className="grid gap-4 px-4 pb-6">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border bg-card p-3 text-sm sm:grid-cols-3">
                <Item label="Capital" value={formatINR(strategy.capital)} />
                <Item label="Risk / trade" value={formatFraction(strategy.risk_per_trade)} />
                <Item label="Stop loss" value={formatFraction(strategy.stop_loss_pct)} />
                <Item label="Target" value={formatFraction(strategy.target_pct)} />
                <Item label="Short selling" value={strategy.allow_short ? "Allowed" : "No"} />
                <Item label="Open qty" value={String(strategy.stats.open_position_qty)} />
                <Item label="Last evaluated" value={formatDateTime(strategy.last_evaluated_at)} />
                <Item label="Last signal" value={formatDateTime(strategy.last_signal_at)} />
                <Item
                  label="Parameters"
                  value={
                    Object.entries(strategy.parameters)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(", ") || "—"
                  }
                />
              </dl>
              {strategy.last_error ? (
                <p className="rounded-md border border-loss/40 bg-loss/10 p-2.5 text-sm text-loss">
                  Last error: {strategy.last_error}
                </p>
              ) : null}
              <div>
                <h3 className="mb-2 text-sm font-semibold">Recent signals</h3>
                <DataTable
                  columns={columns}
                  rows={signals.data}
                  rowKey={(s) => s.id}
                  isLoading={signals.isLoading}
                  error={signals.error}
                  onRetry={() => void signals.refetch()}
                  emptyTitle="No signals yet"
                  emptyDescription="Signals appear once the strategy is running and candles are evaluated."
                />
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="tabular truncate" title={value}>
        {value}
      </dd>
    </div>
  );
}
