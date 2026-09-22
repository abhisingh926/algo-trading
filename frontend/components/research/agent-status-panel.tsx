"use client";

import { X } from "lucide-react";
import { AgentStatusIcon, SyntheticBadge } from "@/components/research/badges";
import { ProgressBar } from "@/components/layout/progress-bar";
import { Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { useNow } from "@/hooks/use-now";
import { isRunActive } from "@/hooks/use-research";
import { formatDuration } from "@/lib/format";
import { AGENT_STATUS_TEXT, istStamp } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { AgentRunRead, AgentStatus, ResearchRunRead } from "@/types/research";

/** The nine research agents in pipeline order, so the panel shows all of them even before the run reports them. */
export const AGENT_ORDER: { agent: string; label: string }[] = [
  { agent: "MarketScannerAgent", label: "Market Scanner" },
  { agent: "MarketResearchAgent", label: "Data Research" },
  { agent: "DataVerificationAgent", label: "Data Verification" },
  { agent: "HistoricalTechnicalAgent", label: "Historical & Technical Analysis" },
  { agent: "FundamentalResearchAgent", label: "Fundamental Analysis" },
  { agent: "NewsCatalystAgent", label: "News & Catalyst Analysis" },
  { agent: "MarketRiskAgent", label: "Market & Risk Analysis" },
  { agent: "QuantScoringAgent", label: "Quant Scoring" },
  { agent: "ResearchSynthesizerAgent", label: "Research Synthesis" },
];

function mergeAgents(run: ResearchRunRead): AgentRunRead[] {
  const reported = new Map((run.agents ?? []).map((a) => [a.agent, a]));
  const merged: AgentRunRead[] = AGENT_ORDER.map(({ agent, label }) => {
    const a = reported.get(agent);
    if (a) return { ...a, label: a.label || label };
    return {
      agent,
      label,
      status: "PENDING",
      started_at: null,
      finished_at: null,
      duration_ms: null,
      records: 0,
      warnings: null,
      message: null,
    };
  });
  // Any agent the backend reports that is not in the known list is appended rather than hidden.
  for (const a of run.agents ?? []) if (!AGENT_ORDER.some((k) => k.agent === a.agent)) merged.push(a);
  return merged;
}

const STATUS_TONE: Partial<Record<AgentStatus, string>> = {
  RUNNING: "text-info",
  FAILED: "text-loss",
  SUCCESS: "text-profit",
  PARTIAL: "text-warning",
};

export function AgentStatusPanel({ run, onDismiss }: { run: ResearchRunRead; onDismiss?: () => void }) {
  const active = isRunActive(run);
  const now = useNow(1000, active);
  const agents = mergeAgents(run);
  // "Done" for progress purposes: anything that will not run further.
  const settled = agents.filter((a) => !["PENDING", "RUNNING"].includes(a.status)).length;
  const started = run.started_at ? new Date(run.started_at).getTime() : null;
  const elapsedMs = run.duration_ms ?? (active && started ? Math.max(0, now - started) : null);
  const failed = run.status === "FAILED";

  return (
    <section aria-label="Agent status" className="rounded-lg border bg-card">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b p-4">
        <h2 className="text-sm font-semibold">Agent Status</h2>
        <span className="tabular text-sm text-muted-foreground">Run #{run.run_number}</span>
        <Pill tone={failed ? "bad" : run.status === "COMPLETED" ? "good" : "info"} dot>
          {run.status}
        </Pill>
        {run.is_synthetic ? <SyntheticBadge /> : null}
        <span className="text-xs text-muted-foreground">
          {run.universe} · {run.depth.charAt(0) + run.depth.slice(1).toLowerCase()}
        </span>
        {onDismiss && !active ? (
          <Button variant="ghost" size="xs" className="ml-auto" onClick={onDismiss}>
            <X /> Hide
          </Button>
        ) : null}
      </div>

      <div className="grid gap-3 p-4">
        <ProgressBar
          value={(settled / agents.length) * 100}
          label="Agents finished"
          barClassName={failed ? "bg-loss" : active ? "bg-info" : "bg-profit"}
        />
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3 lg:grid-cols-6">
          <Meta
            label="Started"
            value={run.started_at ? istStamp(run.started_at) : run.status === "PENDING" ? "Waiting to start" : "—"}
          />
          <Meta label="Duration" value={elapsedMs !== null ? formatDuration(elapsedMs) : "—"} />
          <Meta
            label="Records analysed"
            value={`${run.candidates_analyzed}${run.candidates_scanned ? ` of ${run.candidates_scanned} scanned` : ""}`}
          />
          <Meta label="Sources checked" value={String(run.sources_checked)} />
          <Meta label="Conflicts found" value={String(run.conflicts_found)} />
          <Meta label="Market" value={run.market_state ? run.market_state.replace(/_/g, " ").toLowerCase() : "—"} />
        </dl>

        {failed ? (
          <p role="alert" className="rounded-md border border-loss/40 bg-loss/10 p-2.5 text-sm text-loss">
            <strong>Run failed.</strong> {run.error_message ?? "No error message was provided."}
          </p>
        ) : null}

        <ol className="grid gap-px overflow-hidden rounded-lg border bg-border">
          {agents.map((a) => (
            <li
              key={a.agent}
              className={cn("flex items-start gap-3 bg-card px-3 py-2", a.status === "NOT_AVAILABLE" && "bg-muted/30")}
            >
              <AgentStatusIcon status={a.status} className="mt-0.5" />
              <div className="min-w-0 flex-1 text-sm">
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <span className={cn("font-medium", a.status === "NOT_AVAILABLE" && "text-muted-foreground")}>
                    {a.label}
                  </span>
                  <span className={cn("text-xs", STATUS_TONE[a.status as AgentStatus] ?? "text-muted-foreground")}>
                    {AGENT_STATUS_TEXT[a.status as AgentStatus] ?? a.status}
                  </span>
                </p>
                {a.message ? <p className="text-xs text-muted-foreground">{a.message}</p> : null}
                {a.warnings && a.warnings.length > 0 ? (
                  <p className="text-xs text-warning">{a.warnings.join(" · ")}</p>
                ) : null}
              </div>
              <div className="tabular shrink-0 text-right text-xs text-muted-foreground">
                {a.duration_ms !== null ? <p>{formatDuration(a.duration_ms)}</p> : null}
                {a.records > 0 ? <p>{a.records} records</p> : null}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="tabular truncate" title={value}>
        {value}
      </dd>
    </div>
  );
}
