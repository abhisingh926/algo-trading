import { ClaimStatusBadge } from "@/components/research/badges";
import { Pill } from "@/components/trading/badges";
import { ProgressBar } from "@/components/layout/progress-bar";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { dataAsOf, formatScore, formatUnit, istStamp, SOURCE_TYPE_TEXT } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ConfidenceBreakdown, ResearchReport, SourceValue, VerificationClaim } from "@/types/research";

const BREAKDOWN: { key: keyof Omit<ConfidenceBreakdown, "synthetic_cap_applied">; label: string; help: string }[] = [
  {
    key: "source_reliability",
    label: "Source reliability",
    help: "How trustworthy the sources are. Simulated data scores very low.",
  },
  { key: "freshness", label: "Freshness", help: "How recent the data is compared with the analysis time." },
  { key: "verification", label: "Verification", help: "How many independent sources agree." },
  { key: "completeness", label: "Completeness", help: "How much of the expected data was available." },
  { key: "sample_adequacy", label: "Sample adequacy", help: "Whether the historical samples are large enough." },
];

function formatValue(v: SourceValue["value"]): string {
  if (typeof v === "number") return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 4 }).format(v);
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return v;
}

function ClaimCard({ claim }: { claim: VerificationClaim }) {
  const conflicting = claim.status === "CONFLICTING";
  return (
    <li className={cn("rounded-lg border bg-card p-4", conflicting && "border-loss/50 bg-loss/5")}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <p className="text-sm font-medium">{claim.claim}</p>
        <ClaimStatusBadge status={claim.status} />
        <span className="tabular text-xs text-muted-foreground">
          Confidence {formatUnit(claim.confidence)} · {claim.sources_checked} source
          {claim.sources_checked === 1 ? "" : "s"} · {claim.independent_origins} independent origin
          {claim.independent_origins === 1 ? "" : "s"}
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{claim.detail}</p>
      {conflicting ? (
        <p className="mt-1.5 text-sm font-medium text-loss">The sources disagree. Both values are shown below.</p>
      ) : null}
      {claim.values.length > 0 ? (
        <div className="mt-2 overflow-x-auto rounded-md border">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow className="hover:bg-transparent">
                {["Source", "Origin", "Value", "Data as of", "Reliability"].map((h, i) => (
                  <TableHead
                    key={h}
                    className={cn("h-8 text-xs text-muted-foreground uppercase", i === 2 && "text-right")}
                  >
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {claim.values.map((v, i) => (
                <TableRow key={`${v.source}-${i}`}>
                  <TableCell>{v.source}</TableCell>
                  <TableCell className="text-muted-foreground">{v.origin}</TableCell>
                  <TableCell className={cn("tabular text-right font-medium", conflicting && "text-loss")}>
                    {formatValue(v.value)}
                  </TableCell>
                  <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
                    {istStamp(v.data_as_of)}
                  </TableCell>
                  <TableCell className="tabular">{formatUnit(v.reliability)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">No source values were recorded for this claim.</p>
      )}
      {claim.tolerance_pct !== null ? (
        <p className="mt-1 text-xs text-muted-foreground">Agreement tolerance: {claim.tolerance_pct}%</p>
      ) : null}
      {claim.resolution ? (
        <p className="mt-2 rounded-md bg-muted/50 p-2 text-sm">
          <span className="font-medium">How it was resolved: </span>
          {claim.resolution}
        </p>
      ) : null}
    </li>
  );
}

export function VerificationTab({ report }: { report: ResearchReport }) {
  const v = report.verification;
  const b = v.breakdown;
  return (
    <div className="grid gap-6">
      <section aria-label="Data verification" className="grid gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <h2 className="text-base font-semibold">Data verification</h2>
          <span className="tabular text-sm text-muted-foreground">
            Data Confidence <span className="font-semibold text-foreground">{formatScore(v.data_confidence)}</span> /
            100 · {v.sources_checked} sources checked · {v.conflicts_found} conflicts
          </span>
          <span className="text-xs text-muted-foreground">{dataAsOf(v.provenance.data_as_of)}</span>
        </div>
        {b.synthetic_cap_applied ? (
          <p className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-500">
            Data Confidence is capped at 30 because the prices are synthetic test data. It cannot rise above that until
            a real market data source is used.
          </p>
        ) : null}
        <ul className="grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-5">
          {BREAKDOWN.map((row) => (
            <li key={row.key} className="bg-card px-4 py-3" title={row.help}>
              <p className="text-xs text-muted-foreground">{row.label}</p>
              <p className="tabular text-lg font-semibold">{formatUnit(b[row.key])}</p>
              <ProgressBar value={b[row.key] * 100} label={row.label} className="mt-1" barClassName="bg-info" />
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          A single provider can never reach &quot;Verified&quot;: agreement needs at least two independent origins.
        </p>
      </section>

      <section aria-label="Claims" className="grid gap-2">
        <h3 className="text-sm font-semibold">Claims checked ({v.claims.length})</h3>
        {v.claims.length === 0 ? (
          <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            No claims were verified. Verification is skipped at Quick depth.
          </p>
        ) : (
          <ul className="grid gap-3">
            {v.claims.map((c) => (
              <ClaimCard key={c.key} claim={c} />
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Sources" className="grid gap-2">
        <h3 className="text-sm font-semibold">Sources ({report.sources.length})</h3>
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader className="bg-muted/60">
              <TableRow className="hover:bg-transparent">
                {["Source", "Type", "Tier", "Reliability", "Origin", "Retrieved (IST)", "Data as of (IST)"].map((h) => (
                  <TableHead key={h} className="h-9 text-xs text-muted-foreground uppercase">
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.sources.map((s) => (
                <TableRow key={s.key}>
                  <TableCell className="whitespace-normal">
                    <p className="font-medium">{s.name}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{s.key}</p>
                    {s.note ? <p className="text-xs text-muted-foreground">{s.note}</p> : null}
                  </TableCell>
                  <TableCell>
                    <Pill>{SOURCE_TYPE_TEXT[s.source_type] ?? s.source_type}</Pill>
                  </TableCell>
                  <TableCell className="tabular">{s.tier}</TableCell>
                  <TableCell className="tabular">{formatUnit(s.reliability)}</TableCell>
                  <TableCell className="text-muted-foreground">{s.origin}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">{istStamp(s.retrieved_at)}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">{istStamp(s.data_as_of)}</TableCell>
                </TableRow>
              ))}
              {report.sources.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    No sources were recorded.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}
