import {
  ConflictBanner,
  MarketClosedBanner,
  PartialCoverageBanner,
  ScoreCappedBanner,
  StaleDataBanner,
  SyntheticDataBanner,
} from "@/components/research/banners";
import { Banner } from "@/components/research/banners";
import { SeverityIcon } from "@/components/research/badges";
import type { ResearchReport } from "@/types/research";

/** Banners derived from the report's flags and warnings. Warnings that already have a dedicated banner are not repeated. */
export function ReportBanners({ report }: { report: ResearchReport }) {
  const stale =
    report.market_context.provenance.stale ||
    report.technical.provenance.stale ||
    report.verification.claims.some((c) => c.status === "STALE") ||
    report.warnings.some((w) => /stale/i.test(w.code));
  const staleWarning = report.warnings.find((w) => /stale/i.test(w.code));
  const conflicts = report.verification.conflicts_found;
  const covered = new Set(["SYNTHETIC_DATA", "MARKET_CLOSED", "PARTIAL_COVERAGE", "SCORE_CAPPED"]);
  const other = report.warnings.filter((w) => !covered.has(w.code) && !/stale|conflict/i.test(w.code));

  return (
    <div className="grid gap-2.5">
      {report.is_synthetic ? <SyntheticDataBanner /> : null}
      {report.market_state !== "OPEN" ? (
        <MarketClosedBanner
          note={report.market_context.market_state_note}
          asOf={report.technical.provenance.data_as_of ?? report.as_of}
        />
      ) : null}
      {stale ? <StaleDataBanner message={staleWarning?.message} /> : null}
      {conflicts > 0 ? <ConflictBanner count={conflicts} /> : null}
      {report.score.capped ? (
        <ScoreCappedBanner
          reason={report.score.cap_reason}
          raw={report.score.raw_score}
          capped={report.score.research_score}
        />
      ) : null}
      {report.score_coverage_pct < 100 ? <PartialCoverageBanner pct={report.score_coverage_pct} /> : null}
      {other.map((w) => (
        <Banner
          key={`${w.code}-${w.message}`}
          tone={w.severity === "HIGH" ? "danger" : w.severity === "WARNING" ? "warn" : "info"}
          icon={(p) => <SeverityIcon severity={w.severity} className={p.className} />}
          title={w.message}
        />
      ))}
    </div>
  );
}
