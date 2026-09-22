"use client";

import { CheckCircle2, MinusCircle, XCircle } from "lucide-react";
import { Pill } from "@/components/trading/badges";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { formatDecimal, formatScore, formatUnit, istStamp, SOURCE_TYPE_TEXT } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { EvidenceItem, ScoreComponent, SourceRef } from "@/types/research";

function EvidenceMark({ passed }: { passed: boolean | null }) {
  if (passed === true) return <CheckCircle2 className="size-4 shrink-0 text-profit" aria-label="Passed" />;
  if (passed === false) return <XCircle className="size-4 shrink-0 text-loss" aria-label="Failed" />;
  return <MinusCircle className="size-4 shrink-0 text-muted-foreground" aria-label="Neutral, for information" />;
}

/** One evidence item: tick, cross or neutral mark, its value and the source it cites. */
export function EvidenceRow({ item, sources }: { item: EvidenceItem; sources: SourceRef[] }) {
  const source = item.source_key ? sources.find((s) => s.key === item.source_key) : undefined;
  return (
    <li className="flex gap-2.5">
      <EvidenceMark passed={item.passed} />
      <div className="min-w-0 flex-1 text-sm">
        <p className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span>{item.label}</span>
          <span className="tabular text-muted-foreground">{item.value}</span>
        </p>
        {item.source_key ? (
          <p className="text-xs text-muted-foreground">
            Source: {source ? `${source.name} (${source.key})` : item.source_key}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function SourceCard({ source }: { source: SourceRef }) {
  return (
    <li className="rounded-md border bg-muted/30 p-2.5 text-xs">
      <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
        {source.name} <Pill>{SOURCE_TYPE_TEXT[source.source_type] ?? source.source_type}</Pill>
      </p>
      <dl className="tabular mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-muted-foreground">
        <dt>Reliability</dt>
        <dd className="text-foreground">{formatUnit(source.reliability)}</dd>
        <dt>Origin</dt>
        <dd className="text-foreground">{source.origin}</dd>
        <dt>Retrieved</dt>
        <dd className="text-foreground">{istStamp(source.retrieved_at)}</dd>
        <dt>Data as of</dt>
        <dd className="text-foreground">{istStamp(source.data_as_of)}</dd>
      </dl>
      {source.note ? <p className="mt-1 text-muted-foreground">{source.note}</p> : null}
    </li>
  );
}

interface EvidenceSheetProps {
  component: ScoreComponent | null;
  sources: SourceRef[];
  onOpenChange: (open: boolean) => void;
}

export function EvidenceSheet({ component, sources, onOpenChange }: EvidenceSheetProps) {
  const cited = component
    ? component.sources
        .map((key) => sources.find((s) => s.key === key) ?? null)
        .filter((s): s is SourceRef => s !== null)
    : [];
  const uncitedKeys = component ? component.sources.filter((key) => !sources.some((s) => s.key === key)) : [];
  const metrics = component ? Object.entries(component.metrics) : [];

  return (
    <Sheet open={!!component} onOpenChange={(o) => onOpenChange(o)}>
      <SheetContent className="w-full gap-0 overflow-y-auto data-[side=right]:sm:max-w-lg">
        {component ? (
          <>
            <SheetHeader>
              <SheetTitle className="flex flex-wrap items-center gap-2">
                {component.label}
                {component.available ? (
                  <Pill tone={component.rating === "POOR" ? "bad" : component.rating === "FAIR" ? "warn" : "good"}>
                    {component.rating}
                  </Pill>
                ) : (
                  <Pill>Not assessed</Pill>
                )}
              </SheetTitle>
              <SheetDescription>
                {component.available
                  ? `${formatDecimal(component.points, 2)} of ${formatDecimal(component.max_points, 0)} points`
                  : `Worth up to ${formatDecimal(component.max_points, 0)} points, but could not be assessed, so it is not counted as zero.`}
              </SheetDescription>
            </SheetHeader>
            <div className="grid gap-5 px-4 pb-6">
              <p className="text-sm">{component.summary}</p>

              <section aria-label="Evidence">
                <h3 className="mb-2 text-sm font-semibold">Evidence ({component.evidence.length})</h3>
                {component.evidence.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No evidence items were recorded for this component.</p>
                ) : (
                  <ul className="grid gap-2.5">
                    {component.evidence.map((e, i) => (
                      <EvidenceRow key={`${e.label}-${i}`} item={e} sources={sources} />
                    ))}
                  </ul>
                )}
                <p className="mt-2 text-xs text-muted-foreground">
                  Tick: the rule was met. Cross: it was not. Dash: shown for information only.
                </p>
              </section>

              {metrics.length > 0 ? (
                <section aria-label="Metrics">
                  <h3 className="mb-2 text-sm font-semibold">Underlying figures</h3>
                  <dl className="tabular grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-md border bg-muted/30 p-2.5 text-xs">
                    {metrics.map(([k, v]) => (
                      <div key={k} className="contents">
                        <dt className="text-muted-foreground">{k.replace(/_/g, " ")}</dt>
                        <dd className={cn("text-right break-words")}>
                          {typeof v === "number" ? formatScore(v) : v === null ? "—" : String(v)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ) : null}

              <section aria-label="Sources">
                <h3 className="mb-2 text-sm font-semibold">Sources cited</h3>
                {cited.length === 0 && uncitedKeys.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {component.available
                      ? "This component is derived from the other figures in the report and cites no separate source."
                      : "No source: nothing was available to assess this component."}
                  </p>
                ) : (
                  <ul className="grid gap-2">
                    {cited.map((s) => (
                      <SourceCard key={s.key} source={s} />
                    ))}
                    {uncitedKeys.map((k) => (
                      <li key={k} className="text-xs text-muted-foreground">
                        {k} (not listed in the report sources)
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
