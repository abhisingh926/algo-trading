"use client";

import { AlertTriangle } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { ModeBadge } from "@/components/trading/badges";
import { useStartStrategy } from "@/hooks/use-strategies";
import { formatFraction, formatINR } from "@/lib/format";
import type { Strategy } from "@/types";

interface StartStrategyDialogProps {
  strategy: Strategy | null;
  onOpenChange: (open: boolean) => void;
  onStarted?: (strategy: Strategy) => void;
}

export function StartStrategyDialog({ strategy, onOpenChange, onStarted }: StartStrategyDialogProps) {
  const start = useStartStrategy();
  const live = strategy?.trading_mode === "LIVE";
  return (
    <ConfirmDialog
      open={!!strategy}
      onOpenChange={onOpenChange}
      title={`Start "${strategy?.name ?? ""}"?`}
      description="The strategy will evaluate candles and place orders automatically."
      confirmLabel={live ? "Start LIVE strategy" : "Start strategy"}
      destructive={live}
      pending={start.isPending}
      onConfirm={() => {
        if (!strategy) return;
        start.mutate(strategy.id, {
          onSuccess: (s) => {
            onOpenChange(false);
            onStarted?.(s);
          },
        });
      }}
    >
      {strategy ? (
        <>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-md border bg-muted/40 p-3 text-sm">
            <dt className="text-muted-foreground">Mode</dt>
            <dd>
              <ModeBadge mode={strategy.trading_mode} />
            </dd>
            <dt className="text-muted-foreground">Symbol</dt>
            <dd className="font-medium">
              {strategy.symbol} <span className="text-xs text-muted-foreground">{strategy.exchange} · {strategy.timeframe}</span>
            </dd>
            <dt className="text-muted-foreground">Capital</dt>
            <dd className="tabular font-medium">{formatINR(strategy.capital)}</dd>
            <dt className="text-muted-foreground">Risk / trade</dt>
            <dd className="tabular">{formatFraction(strategy.risk_per_trade)}</dd>
            <dt className="text-muted-foreground">Broker</dt>
            <dd>{strategy.broker_name ?? "System default"}</dd>
          </dl>
          {live ? (
            <p className="flex gap-2 rounded-md border border-loss/40 bg-loss/10 p-2.5 text-sm text-loss">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              LIVE mode places real orders with real money. The backend live-trading guards must all pass
              or orders will be rejected.
            </p>
          ) : null}
        </>
      ) : null}
    </ConfirmDialog>
  );
}
