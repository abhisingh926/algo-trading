"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { RiskBadge, SyntheticBadge } from "@/components/research/badges";
import { useCandidates, useResearchSummary } from "@/hooks/use-research";
import { buttonVariants } from "@/components/ui/button";
import { formatPercent, pnlClass } from "@/lib/format";
import { formatScore, istStamp, reportHref } from "@/lib/research";
import { cn } from "@/lib/utils";

/** Compact dashboard card: latest research run and its top 3 candidates. Hidden until a run exists. */
export function ResearchCard() {
  const summary = useResearchSummary();
  const run = summary.data?.latest_run ?? null;
  const top = useCandidates({ sort: "score", order: "desc", limit: 3 }, !!run);

  if (!run) return null;
  const items = (top.data?.items ?? []).filter((c) => c.stage === "ANALYZED").slice(0, 3);

  return (
    <section aria-label="Research" className="rounded-lg border bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Research</h2>
        <span className="tabular text-xs text-muted-foreground">
          Run #{run.run_number} · {istStamp(run.completed_at ?? run.as_of)}
        </span>
        {run.is_synthetic ? <SyntheticBadge /> : null}
        <Link href="/research" className={cn(buttonVariants({ variant: "ghost", size: "xs" }), "ml-auto")}>
          Open research <ArrowRight />
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-3 text-sm text-muted-foreground">
          {top.isLoading ? "Loading candidates…" : "The latest run has no analysed candidates."}
        </p>
      ) : (
        <div className="px-4 py-2">
          <p className="mb-1 text-xs text-muted-foreground">Top Research Candidates</p>
          <ol className="divide-y">
            {items.map((c) => (
              <li key={c.symbol}>
                <Link
                  href={reportHref(c.symbol)}
                  className="flex items-center gap-3 py-2 text-sm hover:text-foreground/80"
                >
                  <span className="tabular w-4 text-muted-foreground">{c.rank ?? "—"}</span>
                  <span className="min-w-0 flex-1">
                    <span className="font-medium">{c.symbol}</span>
                    <span className="ml-2 hidden truncate text-xs text-muted-foreground sm:inline">{c.company}</span>
                  </span>
                  <span className={cn("tabular hidden text-xs sm:inline", pnlClass(c.change_pct))}>
                    {formatPercent(c.change_pct, 2, true)}
                  </span>
                  <span className="tabular w-20 text-right">
                    <span className="font-semibold">{formatScore(c.research_score)}</span>
                    <span className="text-xs text-muted-foreground"> score</span>
                  </span>
                  {c.risk_level ? <RiskBadge level={c.risk_level} /> : null}
                </Link>
              </li>
            ))}
          </ol>
        </div>
      )}
      <p className="border-t px-4 py-2 text-[11px] text-muted-foreground">
        Research and decision support only, not investment advice.
      </p>
    </section>
  );
}
