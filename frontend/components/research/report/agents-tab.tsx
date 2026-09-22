import { AgentStatusIcon } from "@/components/research/badges";
import { formatDuration } from "@/lib/format";
import { AGENT_STATUS_TEXT, formatUnit, istStamp } from "@/lib/research";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { ResearchReport } from "@/types/research";

/** Accordion of all agents (native details/summary, so it works without extra state and with the keyboard). */
export function AgentsTab({ report }: { report: ResearchReport }) {
  return (
    <section aria-label="Agent findings" className="grid gap-2">
      <div>
        <h2 className="text-base font-semibold">Agent findings and trace</h2>
        <p className="text-xs text-muted-foreground">
          What each research agent did for this report. The synthesis agent only assembles the other agents&apos; output
          and adds no new facts.
        </p>
      </div>
      {report.agents.map((a) => {
        const na = a.status === "NOT_AVAILABLE";
        return (
          <details key={a.agent} className={cn("group rounded-lg border bg-card", na && "bg-muted/30")}>
            <summary className="flex cursor-pointer list-none items-center gap-3 p-3 select-none marker:hidden [&::-webkit-details-marker]:hidden">
              <ChevronRight
                className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90"
                aria-hidden
              />
              <AgentStatusIcon status={a.status} />
              <span className="min-w-0 flex-1">
                <span className={cn("text-sm font-medium", na && "text-muted-foreground")}>{a.label}</span>
                <span className="block truncate text-xs text-muted-foreground">{a.summary}</span>
              </span>
              <span className="tabular hidden shrink-0 text-right text-xs text-muted-foreground sm:block">
                <span className="block">{AGENT_STATUS_TEXT[a.status]}</span>
                {a.duration_ms !== null ? <span className="block">{formatDuration(a.duration_ms)}</span> : null}
              </span>
            </summary>
            <div className="grid gap-3 border-t p-3 pl-10 text-sm">
              <dl className="tabular grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
                <Meta label="Status" value={AGENT_STATUS_TEXT[a.status]} />
                <Meta label="Confidence" value={a.confidence === null ? "—" : formatUnit(a.confidence)} />
                <Meta label="Time (IST)" value={istStamp(a.timestamp)} />
                <Meta label="Duration" value={formatDuration(a.duration_ms)} />
              </dl>
              <p>{a.summary}</p>
              {a.findings.length > 0 ? (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase">Findings</h4>
                  <ul className="mt-1 grid list-disc gap-1 pl-5">
                    {a.findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {a.warnings.length > 0 ? (
                <div>
                  <h4 className="text-xs font-semibold text-warning uppercase">Warnings</h4>
                  <ul className="mt-1 grid list-disc gap-1 pl-5 text-warning">
                    {a.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {a.findings.length === 0 && a.warnings.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  {na ? "This agent has no data source yet, so it produced no findings." : "No further findings."}
                </p>
              ) : null}
            </div>
          </details>
        );
      })}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate text-foreground">{value}</dd>
    </div>
  );
}
