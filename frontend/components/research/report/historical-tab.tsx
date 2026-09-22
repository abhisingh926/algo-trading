import { EmptyState } from "@/components/tables/states";
import { Pill } from "@/components/trading/badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatPercent, pnlClass } from "@/lib/format";
import { dataAsOf, formatPct } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { HistoricalAnalysis, PatternStat } from "@/types/research";

const signed = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? "—" : formatPercent(v, digits, true);

function reach(stat: PatternStat): string {
  const entries = Object.entries(stat.reach_probability);
  if (entries.length === 0) return "—";
  return entries.map(([level, p]) => `${level}%: ${Math.round(p)}%`).join(" · ");
}

function StatRow({ stat, matched }: { stat: PatternStat; matched: boolean }) {
  const ok = stat.sample_adequate;
  return (
    <TableRow className={cn(!ok && "bg-muted/20 text-muted-foreground opacity-60", matched && "bg-info/5")}>
      <TableCell className="w-[26rem] min-w-72 whitespace-normal">
        <p className={cn("font-medium", !ok && "text-muted-foreground")}>
          {stat.label} {matched ? <Pill tone="info">Matches current setup</Pill> : null}
        </p>
        <p className="text-xs text-muted-foreground">{stat.description}</p>
        {stat.note ? <p className="mt-0.5 text-xs">{stat.note}</p> : null}
        {!ok ? (
          <p className="mt-0.5 text-xs font-medium">Sample too small (minimum {stat.min_sample}): no rates shown.</p>
        ) : null}
      </TableCell>
      <TableCell className="whitespace-nowrap">{stat.horizon}</TableCell>
      <TableCell className="tabular text-right">{stat.occurrences}</TableCell>
      <TableCell className="tabular text-right">{ok ? formatPct(stat.success_rate, 1) : "—"}</TableCell>
      <TableCell className={cn("tabular text-right", ok && pnlClass(stat.avg_return_pct))}>
        {ok ? signed(stat.avg_return_pct, 3) : "—"}
      </TableCell>
      <TableCell className={cn("tabular text-right", ok && pnlClass(stat.avg_return_net_pct))}>
        {ok ? signed(stat.avg_return_net_pct, 3) : "—"}
      </TableCell>
      <TableCell className="tabular text-right">{ok ? signed(stat.mfe_pct, 3) : "—"}</TableCell>
      <TableCell className="tabular text-right">{ok ? signed(stat.mae_pct, 3) : "—"}</TableCell>
      <TableCell className="tabular text-xs whitespace-nowrap">{ok ? reach(stat) : "—"}</TableCell>
    </TableRow>
  );
}

export function HistoricalTab({ historical }: { historical: HistoricalAnalysis | null }) {
  if (!historical) {
    return (
      <div className="rounded-lg border bg-card">
        <EmptyState
          title="Historical setup statistics were not run"
          description="They are skipped at Quick depth. Run a Standard or Deep scan to see how similar setups behaved in the past."
        />
      </div>
    );
  }
  const h = historical;
  const matchedKey = h.matched?.key ?? null;
  const baseline = Object.entries(h.baseline_moves);
  const m = h.matched;

  return (
    <div className="grid gap-5">
      <section aria-label="Historical behaviour" className="grid gap-2">
        <h2 className="text-base font-semibold">Historical behaviour</h2>
        <p className="text-xs text-muted-foreground">
          How setups like this one played out in the past on this stock. Past behaviour does not predict what happens
          next, and these figures have not been shown to predict profit.
        </p>
        <dl className="tabular grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border bg-card p-4 text-sm sm:grid-cols-4">
          <Meta label="Sessions analysed" value={String(h.sessions_analyzed)} />
          <Meta
            label="Period"
            value={h.period_start ? `${formatDate(h.period_start)} to ${formatDate(h.period_end)}` : "—"}
          />
          <Meta label="Estimated round-trip cost" value={formatPct(h.estimated_round_trip_cost_pct, 2)} />
          <Meta label="Data" value={dataAsOf(h.provenance.data_as_of)} />
        </dl>
        {h.warnings.length > 0 ? (
          <ul className="grid list-disc gap-1 rounded-lg border border-warning/30 bg-warning/10 p-3 pl-7 text-sm text-warning">
            {h.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section aria-label="Current setup" className="grid gap-2">
        <h3 className="text-sm font-semibold">Current setup and matched sample</h3>
        <div className="rounded-lg border bg-card p-4 text-sm">
          <p>
            <span className="text-muted-foreground">Current setup: </span>
            <span className="font-medium">{h.current_setup_label ?? "Could not be classified"}</span>
          </p>
          {m ? (
            <dl className="tabular mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
              <Meta label="Matched statistic" value={m.label} />
              <Meta label="Horizon" value={m.horizon} />
              <Meta
                label="Occurrences"
                value={`${m.occurrences}${m.successful !== null ? ` (${m.successful} successful)` : ""}`}
              />
              <Meta label="Success rate" value={m.sample_adequate ? formatPct(m.success_rate, 1) : "—"} />
              <Meta label="Average return" value={m.sample_adequate ? signed(m.avg_return_pct, 3) : "—"} />
              <Meta label="Median return" value={m.sample_adequate ? signed(m.median_return_pct, 3) : "—"} />
              <Meta label="Average after costs" value={m.sample_adequate ? signed(m.avg_return_net_pct, 3) : "—"} />
              <Meta
                label="Best / worst excursion"
                value={m.sample_adequate ? `${signed(m.mfe_pct, 3)} / ${signed(m.mae_pct, 3)}` : "—"}
              />
            </dl>
          ) : (
            <p className="mt-2 text-muted-foreground">No past sample matched the current setup closely enough.</p>
          )}
          {m?.note ? <p className="mt-2 text-xs text-muted-foreground">{m.note}</p> : null}
        </div>
      </section>

      {baseline.length > 0 ? (
        <section aria-label="Baseline" className="grid gap-2">
          <h3 className="text-sm font-semibold">Baseline: average move over the same horizons</h3>
          <ul className="tabular grid grid-cols-3 gap-px overflow-hidden rounded-lg border bg-border">
            {baseline.map(([horizon, v]) => (
              <li key={horizon} className="bg-card px-4 py-2.5">
                <p className="text-xs text-muted-foreground">Average {horizon} move</p>
                <p className="text-lg font-semibold">{formatPct(v, 3)}</p>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Compare a setup&apos;s average return with this baseline: a setup only says something if it does better than
            the stock&apos;s ordinary movement, and better than the {formatPct(h.estimated_round_trip_cost_pct, 2)} it
            costs to trade.
          </p>
        </section>
      ) : null}

      <section aria-label="Pattern statistics" className="grid gap-2">
        <h3 className="text-sm font-semibold">Pattern statistics ({h.setups.length})</h3>
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader className="bg-muted/60">
              <TableRow className="hover:bg-transparent">
                {[
                  ["Pattern", "left"],
                  ["Horizon", "left"],
                  ["Occurrences", "right"],
                  ["Success rate", "right"],
                  ["Avg. return", "right"],
                  ["Avg. after costs", "right"],
                  ["MFE", "right"],
                  ["MAE", "right"],
                  ["Reach probability", "left"],
                ].map(([label, align]) => (
                  <TableHead
                    key={label}
                    className={cn("h-9 text-xs text-muted-foreground uppercase", align === "right" && "text-right")}
                  >
                    {label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {h.setups.map((s) => (
                <StatRow key={s.key} stat={s} matched={s.key === matchedKey} />
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground">
          MFE and MAE are the average best and worst price excursion during the horizon. Reach probability is the share
          of occurrences in which price moved that far in the favourable direction. Greyed rows have too few occurrences
          and are shown without rates.
        </p>
      </section>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate" title={value}>
        {value}
      </dd>
    </div>
  );
}
