"use client";

import { useCallback, useRef } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BacktestForm } from "@/components/backtesting/backtest-form";
import { BacktestHistory } from "@/components/backtesting/backtest-history";
import { BacktestResults } from "@/components/backtesting/backtest-results";
import { Section } from "@/components/layout/page-header";

/** State lives in the URL: ?strategy_id= preselects a strategy, ?id= opens a result. */
export function BacktestingView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const strategyId = searchParams.get("strategy_id");
  const backtestId = searchParams.get("id");
  const resultsRef = useRef<HTMLDivElement>(null);

  const setParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(updates)) {
        if (v === null) params.delete(k);
        else params.set(k, v);
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  const openResult = (id: string) => {
    setParams({ id });
    requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  return (
    <div className="grid gap-6">
      <Section title="Configuration">
        <BacktestForm
          initialStrategyId={strategyId}
          onStrategyChange={(id) => setParams({ strategy_id: id })}
          onCompleted={(b) => openResult(b.id)}
        />
      </Section>

      <div ref={resultsRef} className="scroll-mt-20">
        {backtestId ? (
          <Section title="Results">
            <BacktestResults key={backtestId} backtestId={backtestId} />
          </Section>
        ) : null}
      </div>

      <Section title="History" description="Previous backtests. Click a row to open its results.">
        <BacktestHistory
          selectedId={backtestId}
          onOpen={openResult}
          onDeleted={(id) => {
            if (id === backtestId) setParams({ id: null });
          }}
        />
      </Section>
    </div>
  );
}
