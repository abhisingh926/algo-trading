import { RiskBadge, SeverityIcon } from "@/components/research/badges";
import { dataAsOf, formatDecimal } from "@/lib/research";
import type { ResearchReport, RiskLevel } from "@/types/research";

const LEVELS: {
  key: "liquidity_risk" | "volatility_risk" | "event_risk" | "corporate_risk" | "data_risk" | "market_risk";
  label: string;
  help: string;
}[] = [
  { key: "liquidity_risk", label: "Liquidity", help: "Can it be traded in size without moving the price?" },
  { key: "volatility_risk", label: "Volatility", help: "How large and erratic are the price swings?" },
  { key: "event_risk", label: "Event", help: "Results, announcements or other scheduled events." },
  { key: "corporate_risk", label: "Corporate", help: "Governance, surveillance and corporate-action risk." },
  { key: "data_risk", label: "Data", help: "How reliable the underlying data is." },
  { key: "market_risk", label: "Market", help: "Risk from the overall market regime." },
];

export function RiskTab({ report }: { report: ResearchReport }) {
  const r = report.risk;
  return (
    <div className="grid gap-5">
      <section aria-label="Risk levels" className="grid gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-base font-semibold">Risk</h2>
          <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
            Overall <RiskBadge level={r.overall} />
          </span>
          <span className="text-xs text-muted-foreground">{dataAsOf(r.provenance.data_as_of)}</span>
        </div>
        <ul className="grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {LEVELS.map((l) => (
            <li key={l.key} className="bg-card px-4 py-3">
              <p className="flex items-center justify-between gap-2 text-sm font-medium">
                {l.label} <RiskBadge level={r[l.key] as RiskLevel} />
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">{l.help}</p>
              {r[l.key] === "UNKNOWN" ? (
                <p className="mt-0.5 text-xs text-muted-foreground">Not assessed: no data for this yet.</p>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Risk flags" className="grid gap-2">
        <h3 className="text-sm font-semibold">Flags ({r.flags.length})</h3>
        {r.flags.length === 0 ? (
          <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            No risk flags were raised by the checks that could be run. See the list below for what was not checked.
          </p>
        ) : (
          <ul className="grid gap-2 rounded-lg border bg-card p-4">
            {r.flags.map((f) => (
              <li key={`${f.code}-${f.message}`} className="flex gap-2.5 text-sm">
                <SeverityIcon severity={f.severity} className="mt-0.5" />
                <div>
                  <p>{f.message}</p>
                  <p className="text-xs text-muted-foreground">
                    {f.code}
                    {f.metric ? ` · ${f.metric}${f.value !== null ? ` ${formatDecimal(f.value, 2)}` : ""}` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Not checked" className="grid gap-2">
        <h3 className="text-sm font-semibold">Not checked</h3>
        <p className="text-xs text-muted-foreground">
          These risks could not be checked because no data source is connected. Absence of a flag does not mean absence
          of risk.
        </p>
        <ul className="grid list-disc gap-1 rounded-lg border bg-card p-4 pl-8 text-sm">
          {r.unavailable_checks.map((c) => (
            <li key={c}>{c}</li>
          ))}
          {r.unavailable_checks.length === 0 ? (
            <li className="list-none text-muted-foreground">Nothing outstanding.</li>
          ) : null}
        </ul>
      </section>
    </div>
  );
}
