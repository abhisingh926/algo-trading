"use client";

import { useState } from "react";
import { PageHeader, Section } from "@/components/layout/page-header";
import { ResearchDisclaimer } from "@/components/research/disclaimer";
import { SyntheticBadge } from "@/components/research/badges";
import { CandidatesSection } from "@/components/research/candidates-section";
import { ScoreHistoryPanel } from "@/components/research/score-history-panel";
import { DataTable, type Column } from "@/components/tables/data-table";
import { Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCandidates, useResearchRuns } from "@/hooks/use-research";
import { formatDuration, formatNumber } from "@/lib/format";
import { istStamp } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ResearchRunRead } from "@/types/research";

const cap = (s: string) => s.charAt(0) + s.slice(1).toLowerCase();

export function HistoryView() {
  const runs = useResearchRuns(30);
  const latest = useCandidates({ sort: "score", order: "desc", limit: 200 });
  const [openRunId, setOpenRunId] = useState<string | null>(null);
  const [symbolInput, setSymbolInput] = useState("");
  const [symbol, setSymbol] = useState("");

  const openRun = runs.data?.find((r) => r.id === openRunId) ?? null;
  // Default the score-change section to the top candidate so it is not empty on first visit.
  const effectiveSymbol = symbol || latest.data?.items.find((c) => c.stage === "ANALYZED")?.symbol || "";

  const columns: Column<ResearchRunRead>[] = [
    {
      key: "run",
      header: "Run",
      cell: (r) => <span className="tabular font-medium">#{r.run_number}</span>,
    },
    { key: "time", header: "Time (IST)", cell: (r) => istStamp(r.started_at ?? r.created_at) },
    { key: "universe", header: "Universe", hideBelow: "sm", cell: (r) => r.universe },
    { key: "depth", header: "Depth", hideBelow: "md", cell: (r) => cap(r.depth) },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <span title={r.error_message ?? undefined}>
          <Pill tone={r.status === "COMPLETED" ? "good" : r.status === "FAILED" ? "bad" : "info"} dot>
            {r.status}
          </Pill>
        </span>
      ),
    },
    {
      key: "analysed",
      header: "Analysed",
      align: "right",
      cell: (r) => (
        <span className="tabular">
          {formatNumber(r.candidates_analyzed)}
          <span className="text-muted-foreground"> / {formatNumber(r.candidates_scanned)}</span>
        </span>
      ),
    },
    {
      key: "duration",
      header: "Duration",
      align: "right",
      hideBelow: "md",
      cell: (r) => <span className="tabular">{formatDuration(r.duration_ms)}</span>,
    },
    {
      key: "synthetic",
      header: "Data",
      cell: (r) =>
        r.is_synthetic ? (
          <SyntheticBadge />
        ) : (
          <span className="text-xs text-muted-foreground">{r.data_source ?? "—"}</span>
        ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Research History"
        description="Past research runs and how a stock's Research Score changed between them."
      />
      <div className="grid gap-6">
        <ResearchDisclaimer />

        <Section title="Runs" description="Click a run to see the candidates it produced.">
          <DataTable
            columns={columns}
            rows={runs.data}
            rowKey={(r) => r.id}
            isLoading={runs.isLoading}
            error={runs.error}
            onRetry={() => void runs.refetch()}
            onRowClick={(r) => setOpenRunId((cur) => (cur === r.id ? null : r.id))}
            rowClassName={(r) => (r.id === openRunId ? "bg-muted/60" : undefined)}
            maxHeightClass="max-h-96"
            emptyTitle="No research runs yet"
            emptyDescription="Start a New Research Scan on the Research overview. Each run is kept here."
          />
        </Section>

        {openRun ? (
          <div className="grid gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                Candidates from run #{openRun.run_number} ({istStamp(openRun.as_of)})
              </p>
              <Button variant="ghost" size="xs" onClick={() => setOpenRunId(null)}>
                Close
              </Button>
            </div>
            {openRun.status === "COMPLETED" ? (
              <CandidatesSection
                key={openRun.id}
                runId={openRun.id}
                title={`Research candidates: run #${openRun.run_number}`}
              />
            ) : (
              <p className={cn("rounded-lg border bg-card p-4 text-sm", openRun.status === "FAILED" && "text-loss")}>
                {openRun.status === "FAILED"
                  ? `This run failed: ${openRun.error_message ?? "no error message was recorded"}.`
                  : "This run has not finished, so it has no candidates yet."}
              </p>
            )}
          </div>
        ) : null}

        <Section
          title="Score changes"
          description="Choose a symbol to see how its Research Score moved between runs, and why."
        >
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <form
              className="flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                setSymbol(symbolInput.trim().toUpperCase());
              }}
            >
              <Input
                value={symbolInput}
                onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                placeholder={effectiveSymbol ? `Symbol, e.g. ${effectiveSymbol}` : "Symbol, e.g. RELIANCE"}
                aria-label="Symbol for score changes"
                className="w-56"
                list="history-symbols"
                maxLength={20}
              />
              <datalist id="history-symbols">
                {(latest.data?.items ?? []).map((c) => (
                  <option key={c.symbol} value={c.symbol} />
                ))}
              </datalist>
              <Button type="submit" variant="outline" disabled={!symbolInput.trim()}>
                Show
              </Button>
            </form>
            {effectiveSymbol ? (
              <span className="text-sm text-muted-foreground">
                Showing <span className="font-medium text-foreground">{effectiveSymbol}</span>
              </span>
            ) : null}
          </div>
          {effectiveSymbol ? (
            <ScoreHistoryPanel
              key={effectiveSymbol}
              symbol={effectiveSymbol}
              title={`${effectiveSymbol} score history`}
            />
          ) : (
            <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
              Enter a symbol above to see its score history.
            </p>
          )}
        </Section>
      </div>
    </>
  );
}
