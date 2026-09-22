import { MarketContextView } from "@/components/research/market-overview-panel";
import { TrendBadge } from "@/components/research/badges";
import { EmptyState } from "@/components/tables/states";
import { formatPercent } from "@/lib/format";
import { formatDecimal, formatMultiple, formatPct } from "@/lib/research";
import { cn } from "@/lib/utils";
import { pnlClass } from "@/lib/format";
import type { ResearchReport, SectorSnapshot } from "@/types/research";

export function SectorContextCard({ sector }: { sector: SectorSnapshot | null }) {
  if (!sector) {
    return (
      <div className="rounded-lg border bg-card">
        <EmptyState
          title="No sector context"
          description="This stock has no sector assigned in the research universe, or its sector has too few scanned stocks."
        />
      </div>
    );
  }
  const items: { label: string; value: React.ReactNode }[] = [
    { label: "Rank among scanned sectors", value: sector.rank ?? "—" },
    { label: "Trend", value: <TrendBadge trend={sector.trend} /> },
    {
      label: "1D return",
      value: (
        <span className={cn("font-medium", pnlClass(sector.ret_1d_pct))}>
          {formatPercent(sector.ret_1d_pct, 2, true)}
        </span>
      ),
    },
    {
      label: "5D return",
      value: (
        <span className={cn("font-medium", pnlClass(sector.ret_5d_pct))}>
          {formatPercent(sector.ret_5d_pct, 2, true)}
        </span>
      ),
    },
    { label: "Relative strength 1D", value: formatDecimal(sector.rel_strength_1d, 2) },
    { label: "Relative strength 5D", value: formatDecimal(sector.rel_strength_5d, 2) },
    { label: "Avg. relative volume", value: formatMultiple(sector.avg_rel_volume) },
    { label: "Breadth (stocks advancing)", value: formatPct(sector.breadth_pct, 0) },
    { label: "Momentum", value: formatDecimal(sector.momentum, 1) },
    { label: "Stocks scanned in sector", value: sector.constituents },
  ];
  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold">Sector context: {sector.sector}</h3>
      <p className="text-xs text-muted-foreground">
        Computed over the stocks scanned in this run, not the whole sector index.
      </p>
      <dl className="tabular mt-3 grid grid-cols-2 gap-x-6 gap-y-2.5 text-sm sm:grid-cols-3 lg:grid-cols-5">
        {items.map((i) => (
          <div key={i.label} className="min-w-0">
            <dt className="text-xs text-muted-foreground">{i.label}</dt>
            <dd>{i.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function MarketSectorTab({ report }: { report: ResearchReport }) {
  return (
    <div className="grid gap-5">
      <section aria-label="Market context" className="grid gap-2">
        <h2 className="text-base font-semibold">Market context</h2>
        <MarketContextView context={report.market_context} />
      </section>
      <section aria-label="Sector context" className="grid gap-2">
        <h2 className="text-base font-semibold">Sector context</h2>
        <SectorContextCard sector={report.sector_context} />
      </section>
    </div>
  );
}
