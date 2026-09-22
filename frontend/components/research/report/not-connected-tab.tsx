"use client";

import { CircleSlash } from "lucide-react";
import { Pill } from "@/components/trading/badges";
import { useResearchNews } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import type { AgentTrace, ResearchReport } from "@/types/research";

function Card({ title, children, detail }: { title: string; children?: React.ReactNode; detail?: string | null }) {
  return (
    <section className="rounded-lg border border-dashed bg-card p-4" aria-label={title}>
      <div className="flex flex-wrap items-center gap-2">
        <CircleSlash className="size-4 text-muted-foreground" aria-hidden />
        <h3 className="text-sm font-semibold">{title}</h3>
        <Pill>Not connected yet</Pill>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{children}</p>
      {detail ? <p className="mt-2 text-xs text-muted-foreground">{detail}</p> : null}
    </section>
  );
}

const agentMessage = (agents: AgentTrace[], name: string) =>
  agents.find((a) => a.agent === name && a.status === "NOT_AVAILABLE")?.summary ?? null;

/** Sections that have no data source yet. They say so plainly and show nothing made up. */
export function NotConnectedTab({ report }: { report: ResearchReport }) {
  const news = useResearchNews(report.symbol);
  // The endpoint answers 501 today; its own explanation is the honest description of the gap.
  const newsMessage =
    news.error instanceof ApiError
      ? [news.error.message, news.error.description].filter(Boolean).join(": ")
      : news.isLoading
        ? "Checking with the backend…"
        : null;

  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        These parts of a full research picture are not built yet. Nothing is shown for them rather than guessing, and
        the Research Score does not include them.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="News and catalysts" detail={newsMessage}>
          No news source is connected, so recent headlines, catalysts and sentiment for {report.symbol} have not been
          assessed. The Catalyst column shows &quot;Not assessed&quot;.
        </Card>
        <Card title="Corporate events" detail={agentMessage(report.agents, "MarketResearchAgent")}>
          Results dates, dividends, splits, board meetings and announcements are not covered, so event risk around this
          stock is unknown.
        </Card>
        <Card title="Fundamentals" detail={agentMessage(report.agents, "FundamentalResearchAgent")}>
          Revenue, profit, valuation ratios and balance-sheet strength are not covered. The score looks at price and
          volume behaviour only.
        </Card>
        <Card title="Shareholding" detail={agentMessage(report.agents, "FundamentalResearchAgent")}>
          Promoter, institutional (FII/DII) and public holding patterns are not covered.
        </Card>
      </div>
    </div>
  );
}
