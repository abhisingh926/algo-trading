"use client";

import { PageHeader } from "@/components/layout/page-header";
import { ErrorState } from "@/components/tables/states";
import { StrategyForm } from "@/components/trading/strategy-form";
import { Skeleton } from "@/components/ui/skeleton";
import { useStrategy, useStrategyTypes } from "@/hooks/use-strategies";

/** Loads strategy types (and the strategy when editing) before mounting the form. */
export function StrategyBuilder({ strategyId }: { strategyId?: string }) {
  const types = useStrategyTypes();
  const strategy = useStrategy(strategyId ?? null);
  const loading = types.isLoading || (!!strategyId && strategy.isLoading);
  const error = types.error ?? (strategyId ? strategy.error : null);

  return (
    <>
      <PageHeader
        title={strategyId ? "Edit Strategy" : "Create Strategy"}
        description={
          strategyId
            ? (strategy.data?.name ?? "Update the strategy configuration.")
            : "Configure a rule-based strategy. New strategies default to PAPER mode."
        }
      />
      {loading ? (
        <div className="grid max-w-4xl gap-4">
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      ) : error ? (
        <div className="max-w-4xl rounded-lg border bg-card">
          <ErrorState
            error={error}
            onRetry={() => {
              void types.refetch();
              if (strategyId) void strategy.refetch();
            }}
          />
        </div>
      ) : types.data && (!strategyId || strategy.data) ? (
        <StrategyForm key={strategy.data?.id ?? "new"} types={types.data} strategy={strategy.data} />
      ) : null}
    </>
  );
}
