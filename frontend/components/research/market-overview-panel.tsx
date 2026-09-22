"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { ErrorState } from "@/components/tables/states";
import { EmptyState } from "@/components/tables/states";
import { Skeleton } from "@/components/ui/skeleton";
import { MarketStateBadge, RegimeBadge, SyntheticBadge, TrendBadge } from "@/components/research/badges";
import { useResearchMarket } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { dataAsOf, formatDecimal, formatPct, formatUnit } from "@/lib/research";
import { formatPercent, formatPrice, pnlClass } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Breadth, IndexSnapshot, MarketContext, RegimeFactor } from "@/types/research";

function Tile({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-0 bg-card px-4 py-3", className)}>
      <p className="truncate text-xs font-medium text-muted-foreground">{label}</p>
      {children}
    </div>
  );
}

function IndexTile({ index }: { index: IndexSnapshot }) {
  return (
    <Tile label={index.name}>
      {index.available ? (
        <>
          <p className="tabular mt-0.5 text-lg font-semibold">{formatPrice(index.price)}</p>
          <p className="tabular flex flex-wrap items-center gap-x-2 text-xs">
            <span className={cn("font-medium", pnlClass(index.change_pct))}>
              {formatPercent(index.change_pct, 2, true)}
            </span>
            <TrendBadge trend={index.trend} />
          </p>
          <p className="tabular mt-1 text-xs text-muted-foreground">
            RSI {formatDecimal(index.rsi, 0)} · 5D {formatPercent(index.ret_5d_pct, 2, true)}
          </p>
        </>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">Not available</p>
      )}
    </Tile>
  );
}

function BreadthTiles({ breadth }: { breadth: Breadth | null }) {
  if (!breadth) {
    return (
      <Tile label="Advance / decline" className="sm:col-span-2">
        <p className="mt-1 text-sm text-muted-foreground">Not available</p>
      </Tile>
    );
  }
  const total = breadth.advances + breadth.declines + breadth.unchanged || 1;
  return (
    <>
      <Tile label="Advance / decline">
        <p className="tabular mt-0.5 text-lg font-semibold">
          <span className="text-profit">{breadth.advances}</span>
          <span className="text-muted-foreground"> / </span>
          <span className="text-loss">{breadth.declines}</span>
        </p>
        <div
          className="mt-1 flex h-1.5 overflow-hidden rounded-full bg-muted"
          role="img"
          aria-label={`${breadth.advances} advancing, ${breadth.declines} declining, ${breadth.unchanged} unchanged`}
        >
          <span className="bg-profit" style={{ width: `${(breadth.advances / total) * 100}%` }} />
          <span className="bg-muted-foreground/40" style={{ width: `${(breadth.unchanged / total) * 100}%` }} />
          <span className="bg-loss" style={{ width: `${(breadth.declines / total) * 100}%` }} />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          of {breadth.universe_size} scanned · {breadth.unchanged} unchanged
        </p>
      </Tile>
      <Tile label="Breadth">
        <p className="tabular mt-0.5 text-lg font-semibold">{formatPct(breadth.pct_above_vwap, 0)}</p>
        <p className="text-xs text-muted-foreground">above VWAP</p>
        <p className="tabular text-xs text-muted-foreground">
          {formatPct(breadth.pct_above_ema20, 0)} above 20-day EMA
        </p>
      </Tile>
    </>
  );
}

function FactorRow({ factor }: { factor: RegimeFactor }) {
  const Icon = factor.bullish === true ? ArrowUpRight : factor.bullish === false ? ArrowDownRight : Minus;
  const cls =
    factor.bullish === true ? "text-profit" : factor.bullish === false ? "text-loss" : "text-muted-foreground";
  return (
    <li className="flex gap-2 text-sm">
      <Icon
        className={cn("mt-0.5 size-4 shrink-0", cls)}
        aria-label={factor.bullish === true ? "Bullish" : factor.bullish === false ? "Bearish" : "Neutral"}
      />
      <div className="min-w-0">
        <p>
          <span className="font-medium">{factor.name}</span>{" "}
          <span className="tabular text-muted-foreground">{factor.value}</span>
        </p>
        <p className="text-xs text-muted-foreground">{factor.detail}</p>
      </div>
    </li>
  );
}

/** Regime, factor list and the index tiles for one market context. Reused by the stock report. */
export function MarketContextView({ context }: { context: MarketContext }) {
  const nifty = context.indices.find((i) => i.symbol === "NIFTY");
  const bank = context.indices.find((i) => i.symbol === "BANKNIFTY");
  const others = context.indices.filter((i) => i !== nifty && i !== bank);
  const ordered = [nifty, bank, ...others].filter((i): i is IndexSnapshot => !!i);
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-3 xl:grid-cols-5">
        {ordered.map((i) => (
          <IndexTile key={i.symbol} index={i} />
        ))}
        <Tile label="India VIX">
          {context.india_vix !== null ? (
            <>
              <p className="tabular mt-0.5 text-lg font-semibold">{formatDecimal(context.india_vix, 2)}</p>
              <p className="tabular text-xs text-muted-foreground">
                {formatPercent(context.india_vix_change_pct, 2, true)} day
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Not available</p>
          )}
        </Tile>
        <BreadthTiles breadth={context.breadth} />
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <h3 className="text-sm font-semibold">Market Regime</h3>
          <RegimeBadge label={context.regime.label} />
          <span className="tabular text-xs text-muted-foreground">
            Confidence {formatUnit(context.regime.confidence)} · Volatility {context.regime.volatility.toLowerCase()}
          </span>
        </div>
        {context.regime.factors.length > 0 ? (
          <ul className="mt-3 grid gap-x-8 gap-y-2.5 md:grid-cols-2">
            {context.regime.factors.map((f) => (
              <FactorRow key={f.name} factor={f} />
            ))}
          </ul>
        ) : null}
        <p className="mt-3 text-xs text-muted-foreground">
          {dataAsOf(context.provenance.data_as_of)} · source {context.provenance.source}
          {context.breadth ? ` · ${context.breadth.note}` : ""}
        </p>
        {context.unavailable && context.unavailable.length > 0 ? (
          <p className="mt-1 text-xs text-muted-foreground">Not available: {context.unavailable.join("; ")}</p>
        ) : null}
      </div>
    </div>
  );
}

export function MarketOverviewPanel() {
  const { data, isLoading, error, refetch } = useResearchMarket();

  if (isLoading) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error && !data) {
    const noRun = error instanceof ApiError && error.code === 404;
    return (
      <div className="rounded-lg border bg-card">
        {noRun ? (
          <EmptyState
            title="No market overview yet"
            description="The market overview is built by a research scan. Start a New Research Scan to see indices, breadth and the market regime."
          />
        ) : (
          <ErrorState error={error} onRetry={() => void refetch()} />
        )}
      </div>
    );
  }
  if (!data) return null;
  const ctx = data.context;
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <MarketStateBadge state={ctx.market_state} />
        {data.is_synthetic ? <SyntheticBadge /> : null}
        <span>Run #{data.run_number}</span>
        <span>· Source: {data.data_source ?? "unknown"}</span>
      </div>
      <MarketContextView context={ctx} />
    </div>
  );
}
