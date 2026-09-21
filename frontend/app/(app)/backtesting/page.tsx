import { Suspense } from "react";
import type { Metadata } from "next";
import { BacktestingView } from "@/components/backtesting/backtesting-view";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Backtesting" };

export default function BacktestingPage() {
  return (
    <>
      <PageHeader
        title="Backtesting"
        description="Replay a strategy on historical candles with brokerage, slippage and statutory charges."
      />
      <Suspense fallback={<Skeleton className="h-72 w-full" />}>
        <BacktestingView />
      </Suspense>
    </>
  );
}
