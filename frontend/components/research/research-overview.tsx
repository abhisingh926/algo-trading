"use client";

import { useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { PageHeader, Section } from "@/components/layout/page-header";
import { AgentStatusPanel } from "@/components/research/agent-status-panel";
import { MarketClosedBanner, SyntheticDataBanner } from "@/components/research/banners";
import { CandidatesSection } from "@/components/research/candidates-section";
import { ResearchDisclaimer } from "@/components/research/disclaimer";
import { MarketOverviewPanel } from "@/components/research/market-overview-panel";
import { RunDialog } from "@/components/research/run-dialog";
import { SymbolSearch } from "@/components/research/symbol-search";
import { Button } from "@/components/ui/button";
import {
  isRunActive,
  useCandidates,
  useRefreshResearchData,
  useResearchMarket,
  useResearchRun,
  useResearchSummary,
} from "@/hooks/use-research";
import type { ResearchRunRead } from "@/types/research";

interface Tracked {
  id: string;
  seed: ResearchRunRead | null;
}

export function ResearchOverview() {
  const summary = useResearchSummary();
  const market = useResearchMarket();
  // Same query key the table uses for its default view: only used here for symbol suggestions.
  const suggestionsQuery = useCandidates({ sort: "score", order: "desc", limit: 200 });
  const refresh = useRefreshResearchData();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tracked, setTracked] = useState<Tracked | null>(null);
  // A run the user hid after it finished: the summary may still list it as active for a few seconds.
  const [hidden, setHidden] = useState<string | null>(null);

  // Follow a run that is already active (for example started before a page refresh).
  const activeId = summary.data?.active_run?.id ?? null;
  if (activeId && activeId !== hidden && tracked?.id !== activeId)
    setTracked({ id: activeId, seed: summary.data?.active_run ?? null });

  const polled = useResearchRun(tracked?.id ?? null);
  const run = polled.data ?? tracked?.seed ?? null;

  // When the tracked run reaches a terminal state, refresh every research view once.
  const refreshedFor = useRef<string | null>(null);
  useEffect(() => {
    if (polled.data && !isRunActive(polled.data) && refreshedFor.current !== polled.data.id) {
      refreshedFor.current = polled.data.id;
      refresh();
    }
  }, [polled.data, refresh]);

  const latest = summary.data?.latest_run ?? null;
  const active = isRunActive(run) || !!summary.data?.active_run;
  const synthetic = market.data?.is_synthetic ?? latest?.is_synthetic ?? false;
  const ctx = market.data?.context;

  return (
    <>
      <PageHeader
        title="Research"
        description="AI-assisted market research for Indian stocks: ranked candidates, the evidence behind each score, and what is not covered yet."
        actions={
          <>
            <SymbolSearch suggestions={suggestionsQuery.data?.items.map((c) => c.symbol) ?? []} />
            <Button onClick={() => setDialogOpen(true)} disabled={active}>
              <Play /> New Research Scan
            </Button>
          </>
        }
      />
      <div className="grid gap-5">
        <ResearchDisclaimer />
        {synthetic ? <SyntheticDataBanner /> : null}
        {ctx && ctx.market_state !== "OPEN" ? (
          <MarketClosedBanner note={ctx.market_state_note} asOf={ctx.provenance.data_as_of ?? ctx.as_of} />
        ) : null}

        {tracked && run ? (
          <AgentStatusPanel
            run={run}
            onDismiss={() => {
              setHidden(tracked.id);
              setTracked(null);
            }}
          />
        ) : null}

        <Section
          title="Market Overview"
          description="Indices, breadth and the market regime used as context for every score."
        >
          <MarketOverviewPanel />
        </Section>

        <CandidatesSection onStartScan={() => setDialogOpen(true)} scanActive={active} />
      </div>

      <RunDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onStarted={(started) => setTracked({ id: started.id, seed: started })}
        disabledReason={active ? "A research run is already in progress. Wait for it to finish." : null}
      />
    </>
  );
}
