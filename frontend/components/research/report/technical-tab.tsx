import { CheckCircle2, MinusCircle, XCircle } from "lucide-react";
import { DirectionBadge, TrendBadge } from "@/components/research/badges";
import { Pill } from "@/components/trading/badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatPercent, formatPrice, pnlClass } from "@/lib/format";
import { dataAsOf, formatDecimal, formatMultiple, formatPct, humanizeKey } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { IntradayLevels, ResearchReport, TimeframeTechnical } from "@/types/research";

const STACK_TONE = { BULLISH: "good", BEARISH: "bad", MIXED: "warn", UNKNOWN: "neutral" } as const;

function TimeframeTable({ rows }: { rows: TimeframeTechnical[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border bg-card">
      <Table>
        <TableHeader className="bg-muted/60">
          <TableRow className="hover:bg-transparent">
            {[
              "Timeframe",
              "Bars",
              "Trend",
              "EMA stack",
              "RSI",
              "MACD hist.",
              "ADX",
              "ATR",
              "BB width",
              "Rel. volume",
            ].map((h, i) => (
              <TableHead key={h} className={cn("h-9 text-xs text-muted-foreground uppercase", i > 3 && "text-right")}>
                {h}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((t) => (
            <TableRow key={t.timeframe}>
              <TableCell className="font-medium">{t.timeframe}</TableCell>
              <TableCell className="tabular text-muted-foreground">{t.bars}</TableCell>
              <TableCell>
                <TrendBadge trend={t.trend} />
              </TableCell>
              <TableCell>
                <Pill tone={STACK_TONE[t.ema_stack]}>{humanizeKey(t.ema_stack)}</Pill>
              </TableCell>
              <TableCell className="tabular text-right">{formatDecimal(t.rsi, 1)}</TableCell>
              <TableCell
                className={cn("tabular text-right", pnlClass(t.macd_hist))}
                title={`MACD ${formatDecimal(t.macd, 3)} · signal ${formatDecimal(t.macd_signal, 3)}`}
              >
                {formatDecimal(t.macd_hist, 3)}
              </TableCell>
              <TableCell className="tabular text-right">{formatDecimal(t.adx, 1)}</TableCell>
              <TableCell className="tabular text-right">{formatDecimal(t.atr, 2)}</TableCell>
              <TableCell className="tabular text-right">{formatPct(t.bb_width_pct, 2)}</TableCell>
              <TableCell className="tabular text-right">{formatMultiple(t.rel_volume)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function Mark({ passed }: { passed: boolean | null }) {
  if (passed === true)
    return <CheckCircle2 className="size-4 shrink-0 text-profit" aria-label="Supports the direction" />;
  if (passed === false) return <XCircle className="size-4 shrink-0 text-loss" aria-label="Against the direction" />;
  return <MinusCircle className="size-4 shrink-0 text-muted-foreground" aria-label="Neutral" />;
}

/** All price levels sorted high to low with the current price inserted, and the distance from it. */
function LevelsLadder({ levels, price }: { levels: IntradayLevels; price: number }) {
  const rows: { label: string; value: number; kind: "res" | "sup" | "ref" | "price" }[] = [];
  const add = (label: string, value: number | null | undefined, kind: "res" | "sup" | "ref") => {
    if (value !== null && value !== undefined) rows.push({ label, value, kind });
  };
  levels.resistance.forEach((v, i) => add(`Resistance ${i + 1}`, v, "res"));
  levels.support.forEach((v, i) => add(`Support ${i + 1}`, v, "sup"));
  add("Prior day high", levels.prev_day_high, "ref");
  add("Prior day low", levels.prev_day_low, "ref");
  add("Prior day close", levels.prev_day_close, "ref");
  add("Opening range high (15m)", levels.opening_range_15_high, "ref");
  add("Opening range low (15m)", levels.opening_range_15_low, "ref");
  if (levels.opening_range_30_high !== levels.opening_range_15_high)
    add("Opening range high (30m)", levels.opening_range_30_high, "ref");
  if (levels.opening_range_30_low !== levels.opening_range_15_low)
    add("Opening range low (30m)", levels.opening_range_30_low, "ref");
  add("VWAP", levels.vwap, "ref");
  rows.push({ label: "Current price", value: price, kind: "price" });
  rows.sort((a, b) => b.value - a.value);
  return (
    <ul className="divide-y rounded-lg border bg-card text-sm" aria-label="Price levels, highest first">
      {rows.map((r) => (
        <li
          key={`${r.label}-${r.value}`}
          className={cn(
            "flex items-center justify-between gap-3 px-3 py-1.5",
            r.kind === "price" && "bg-info/10 font-semibold",
          )}
        >
          <span
            className={cn(
              r.kind === "res" && "text-loss",
              r.kind === "sup" && "text-profit",
              r.kind === "ref" && "text-muted-foreground",
            )}
          >
            {r.label}
          </span>
          <span className="tabular flex items-baseline gap-3">
            <span>{formatPrice(r.value)}</span>
            <span className="w-16 text-right text-xs text-muted-foreground">
              {r.kind === "price" ? "" : formatPercent(((r.value - price) / price) * 100, 2, true)}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export function TechnicalTab({ report }: { report: ResearchReport }) {
  const t = report.technical;
  const pa = t.price_action;
  const lv = t.levels;
  const flags: { label: string; value: string }[] = [
    { label: "Structure", value: humanizeKey(pa.structure) },
    { label: "Swings", value: `${pa.swing_highs} highs · ${pa.swing_lows} lows` },
    {
      label: "Breakout",
      value: pa.breakout
        ? `${humanizeKey(pa.breakout)}${pa.breakout_level ? ` through ${formatPrice(pa.breakout_level)}` : ""}`
        : "None",
    },
    { label: "20-day breakout", value: pa.breakout_20d ? humanizeKey(pa.breakout_20d) : "None" },
    { label: "Consolidation", value: pa.consolidation ? "Yes" : "No" },
    { label: "Range expansion", value: pa.range_expansion ? "Yes" : "No" },
    { label: "Stretched", value: pa.stretched ? humanizeKey(pa.stretched) : "No" },
    { label: "VWAP event", value: pa.vwap_event ? humanizeKey(pa.vwap_event) : "None" },
    { label: "Price and volume", value: humanizeKey(pa.price_volume) },
  ];
  const gapText =
    lv.gap_pct === null
      ? "—"
      : `${formatPercent(lv.gap_pct, 2, true)} ${lv.gap_direction === "NONE" ? "" : lv.gap_direction.toLowerCase()}${
          lv.gap_filled_today === null ? "" : lv.gap_filled_today ? " (filled today)" : " (not filled)"
        }`;

  return (
    <div className="grid gap-6">
      <section aria-label="Technical analysis" className="grid gap-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h2 className="text-base font-semibold">Technical analysis</h2>
          <DirectionBadge direction={t.direction} />
          <span className="text-xs text-muted-foreground">
            {dataAsOf(t.provenance.data_as_of)} · {t.provenance.note ?? t.provenance.source}
          </span>
        </div>
        <TimeframeTable rows={t.timeframes} />

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-sm font-semibold">Price action</h3>
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              {flags.map((f) => (
                <div key={f.label} className="min-w-0">
                  <dt className="text-xs text-muted-foreground">{f.label}</dt>
                  <dd className="truncate" title={f.value}>
                    {f.value}
                  </dd>
                </div>
              ))}
            </dl>
            {pa.tags.length > 0 ? (
              <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Price action tags">
                {pa.tags.map((tag) => (
                  <li key={tag} className="rounded-md border bg-muted/40 px-2 py-0.5 text-xs">
                    {tag}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              Direction votes <DirectionBadge direction={t.direction} />
            </h3>
            <p className="text-xs text-muted-foreground">
              Each signal votes +1, 0 or -1 on the direction of the setup.
            </p>
            <ul className="mt-2 grid gap-2">
              {t.direction_votes.map((v) => (
                <li key={v.label} className="flex items-center gap-2.5 text-sm">
                  <Mark passed={v.passed} />
                  <span className="flex-1">{v.label}</span>
                  <span className="tabular text-muted-foreground">{v.value}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section aria-label="Intraday setup" className="grid gap-3">
        <h2 className="text-base font-semibold">Intraday setup</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border bg-card p-4">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <Item label="VWAP" value={formatPrice(lv.vwap)} />
              <Item
                label="Price vs VWAP"
                value={
                  lv.vwap_position
                    ? `${humanizeKey(lv.vwap_position)}${lv.vwap_distance_pct !== null ? ` (${formatPercent(lv.vwap_distance_pct, 2, true)})` : ""}`
                    : "—"
                }
              />
              <Item
                label="Opening range (15m)"
                value={`${formatPrice(lv.opening_range_15_low)} – ${formatPrice(lv.opening_range_15_high)}`}
              />
              <Item
                label="Opening range (30m)"
                value={`${formatPrice(lv.opening_range_30_low)} – ${formatPrice(lv.opening_range_30_high)}`}
              />
              <Item
                label="Prior day high / low"
                value={`${formatPrice(lv.prev_day_high)} / ${formatPrice(lv.prev_day_low)}`}
              />
              <Item label="Prior day close" value={formatPrice(lv.prev_day_close)} />
              <Item label="Gap" value={gapText} />
            </dl>
          </div>
          <LevelsLadder levels={lv} price={report.price.price} />
        </div>
      </section>
    </div>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="tabular truncate" title={value}>
        {value}
      </dd>
    </div>
  );
}
