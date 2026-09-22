import { ExportButtons } from "@/components/research/report/export-buttons";
import {
  DirectionBadge,
  MarketStateBadge,
  QualityBadge,
  RiskBadge,
  SyntheticBadge,
} from "@/components/research/badges";
import { ProgressBar } from "@/components/layout/progress-bar";
import { formatINR, formatPercent, formatPrice, pnlClass } from "@/lib/format";
import { dataAsOf, DIRECTION_TEXT, formatScore, istStamp, LABEL_ORDER, humanizeKey } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ResearchReport } from "@/types/research";

function BigNumber({
  title,
  value,
  caption,
  bar,
  barClass,
  id,
}: {
  title: string;
  value: string;
  caption: React.ReactNode;
  bar: number | null;
  barClass?: string;
  id: string;
}) {
  return (
    <div className="min-w-0 rounded-lg border bg-card px-4 py-3" aria-labelledby={id}>
      <p id={id} className="text-xs font-medium text-muted-foreground">
        {title}
      </p>
      <p className="tabular mt-0.5 flex items-baseline gap-1">
        <span className="text-4xl font-semibold tracking-tight">{value}</span>
        <span className="text-sm text-muted-foreground">/ 100</span>
      </p>
      <ProgressBar value={bar ?? 0} label={title} className="mt-2" barClassName={barClass} />
      <p className="mt-1.5 text-xs text-muted-foreground">{caption}</p>
    </div>
  );
}

/** Label chips in reading order; the direction chip comes from the report field, the rest from report.labels. */
function chipEntries(report: ResearchReport): { title: string; value: string }[] {
  const seen = new Set<string>();
  const out: { title: string; value: string }[] = [];
  for (const { key, title } of LABEL_ORDER) {
    const value = key === "direction" ? DIRECTION_TEXT[report.direction] : report.labels[key];
    if (value) out.push({ title, value });
    seen.add(key);
  }
  for (const [key, value] of Object.entries(report.labels)) {
    if (!seen.has(key) && value) out.push({ title: humanizeKey(key), value });
  }
  return out;
}

export function ReportHeader({ report }: { report: ResearchReport }) {
  const chips = chipEntries(report);
  const o = report.overview;
  return (
    <header className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h1 className="font-heading text-2xl font-semibold tracking-tight">{report.symbol}</h1>
            <MarketStateBadge state={report.market_state} />
            {report.is_synthetic ? <SyntheticBadge /> : null}
          </div>
          <p className="text-sm text-muted-foreground">
            {report.company}
            {report.sector ? ` · ${report.sector}` : ""}
            {o.industry ? ` · ${o.industry}` : ""} · {o.exchange}
          </p>
          <p className="tabular mt-1 flex flex-wrap items-baseline gap-x-3 text-sm">
            <span className="text-xl font-semibold">{formatINR(o.price)}</span>
            <span className={cn("font-medium", pnlClass(o.change))}>
              {formatPercent(o.change_pct, 2, true)}
              {o.change !== null ? ` (${o.change >= 0 ? "+" : "-"}${formatPrice(Math.abs(o.change))})` : ""}
            </span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {dataAsOf(report.technical.provenance.data_as_of ?? report.as_of)} · analysed {istStamp(report.as_of)} ·
            source {report.data_source}
          </p>
        </div>
        <ExportButtons symbol={report.symbol} runId={report.run_id} />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1.4fr]">
        <BigNumber
          id="rs-title"
          title="Research Score"
          value={report.research_score === null ? "—" : formatScore(report.research_score)}
          bar={report.research_score}
          barClass="bg-info"
          caption={
            <>
              {report.research_score === null ? "Not enough data to score. " : ""}
              Covers {Math.round(report.score_coverage_pct)}% of scoring weights
              {report.score.weight_set_version ? ` · weights v${report.score.weight_set_version}` : ""}
            </>
          }
        />
        <BigNumber
          id="dc-title"
          title="Data Confidence"
          value={formatScore(report.data_confidence)}
          bar={report.data_confidence}
          barClass={report.data_confidence < 40 ? "bg-warning" : "bg-profit"}
          caption="How far the underlying data can be trusted. A separate number from the score."
        />
        <div className="flex min-w-0 flex-col justify-center gap-2 rounded-lg border bg-card px-4 py-3 md:col-span-2 xl:col-span-1">
          <div className="flex flex-wrap items-center gap-2">
            <QualityBadge quality={report.setup_quality} />
            <DirectionBadge direction={report.direction} />
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              Risk <RiskBadge level={report.risk_level} />
            </span>
          </div>
          <ul className="flex flex-wrap gap-1.5" aria-label="Report labels">
            {chips.map((c) => (
              <li
                key={c.title}
                className="rounded-md border bg-muted/40 px-2 py-0.5 text-xs"
                title={`${c.title}: ${c.value}`}
              >
                <span className="text-muted-foreground">{c.title}: </span>
                <span className="font-medium">{c.value}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </header>
  );
}
