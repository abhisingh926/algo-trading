"use client";

import { AlertTriangle } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { ModeBadge } from "@/components/trading/badges";
import { StrategyReviewPanel } from "@/components/trading/strategy-review-panel";
import { useStrategyReview } from "@/hooks/use-guide";
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
  const review = useStrategyReview(strategy?.id ?? null);
  const live = strategy?.trading_mode === "LIVE";
  const paper = strategy?.trading_mode === "PAPER";
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
          <StrategyReviewPanel
            variant="compact"
            title="Good-practice review"
            review={review.data}
            isLoading={review.isLoading}
            isFetching={review.isFetching}
            error={review.error}
            onRetry={() => void review.refetch()}
          />
          {review.data?.verdict === "NOT_RECOMMENDED" ? (
            <p
              role="note"
              className="flex gap-2 rounded-md border border-loss/40 bg-loss/10 p-2.5 text-sm text-loss"
            >
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {paper
                ? "The review found serious issues. You can still start in paper mode."
                : `The review found serious issues. Starting in ${strategy.trading_mode} mode is strongly discouraged: switch this strategy to PAPER mode and fix them first. The Start button stays enabled, but the risk is yours.`}
            </p>
          ) : null}
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
