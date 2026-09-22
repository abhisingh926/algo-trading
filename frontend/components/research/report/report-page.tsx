"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/tables/states";
import { ResearchDisclaimer } from "@/components/research/disclaimer";
import { AgentsTab } from "@/components/research/report/agents-tab";
import { HistoricalTab } from "@/components/research/report/historical-tab";
import { InsightLists } from "@/components/research/report/insight-lists";
import { MarketSectorTab } from "@/components/research/report/market-sector-tab";
import { NotConnectedTab } from "@/components/research/report/not-connected-tab";
import { PriceChart } from "@/components/research/report/price-chart";
import { ReportBanners } from "@/components/research/report/report-banners";
import { ReportHeader } from "@/components/research/report/report-header";
import { RiskTab } from "@/components/research/report/risk-tab";
import { ScoreBreakdown } from "@/components/research/report/score-breakdown";
import { TechnicalTab } from "@/components/research/report/technical-tab";
import { VerificationTab } from "@/components/research/report/verification-tab";
import { ScoreHistoryPanel } from "@/components/research/score-history-panel";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useResearchReport } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { decodeSymbol } from "@/lib/research";

export function ReportPage({ rawSymbol }: { rawSymbol: string }) {
  const symbol = decodeSymbol(rawSymbol);
  const runId = useSearchParams().get("run_id");
  const { data: report, isLoading, error, refetch } = useResearchReport(symbol, runId);

  const back = (
    <Link href="/research" className={buttonVariants({ variant: "ghost", size: "sm" }) + " -ml-2 mb-2 w-fit"}>
      <ArrowLeft /> Research
    </Link>
  );

  if (isLoading) {
    return (
      <div className="grid gap-4">
        {back}
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !report) {
    const notFound = error instanceof ApiError && error.code === 404;
    return (
      <div className="grid gap-4">
        {back}
        <ResearchDisclaimer />
        <div className="rounded-lg border bg-card">
          {notFound ? (
            <EmptyState
              title={`No research report for ${symbol} yet`}
              description="A report exists only for stocks that were part of a research scan. Start a New Research Scan on the overview page, using a custom list that includes this symbol."
              action={
                <Link href="/research" className={buttonVariants({ size: "sm" })}>
                  Go to Research
                </Link>
              }
            />
          ) : (
            <ErrorState error={error ?? new Error("Report not found")} onRetry={() => void refetch()} />
          )}
        </div>
      </div>
    );
  }

  const tabs = [
    { value: "overview", label: "Score & evidence" },
    { value: "market", label: "Market & sector" },
    { value: "technical", label: "Technical & intraday" },
    { value: "historical", label: "Historical" },
    { value: "chart", label: "Chart" },
    { value: "risk", label: "Risk" },
    { value: "data", label: "Data & sources" },
    { value: "missing", label: "Not connected" },
    { value: "agents", label: "Agents" },
  ];

  return (
    <div className="grid gap-4">
      {back}
      <ResearchDisclaimer text={report.disclaimer} />
      <ReportHeader report={report} />
      <ReportBanners report={report} />

      <Tabs defaultValue="overview" className="gap-4">
        <div className="overflow-x-auto pb-1">
          <TabsList className="w-max">
            {tabs.map((t) => (
              <TabsTrigger key={t.value} value={t.value} className="px-3">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <TabsContent value="overview" className="grid gap-6">
          <ScoreBreakdown report={report} />
          <InsightLists report={report} />
          <ScoreHistoryPanel symbol={report.symbol} />
        </TabsContent>
        <TabsContent value="market">
          <MarketSectorTab report={report} />
        </TabsContent>
        <TabsContent value="technical">
          <TechnicalTab report={report} />
        </TabsContent>
        <TabsContent value="historical">
          <HistoricalTab historical={report.historical} />
        </TabsContent>
        <TabsContent value="chart">
          <PriceChart report={report} />
        </TabsContent>
        <TabsContent value="risk">
          <RiskTab report={report} />
        </TabsContent>
        <TabsContent value="data">
          <VerificationTab report={report} />
        </TabsContent>
        <TabsContent value="missing">
          <NotConnectedTab report={report} />
        </TabsContent>
        <TabsContent value="agents">
          <AgentsTab report={report} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
