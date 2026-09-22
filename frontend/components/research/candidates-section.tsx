"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, ArrowUpDown, Play, X } from "lucide-react";
import { Field, parseNumber, SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ErrorState } from "@/components/tables/states";
import { EmptyState } from "@/components/tables/states";
import { RiskBadge, SyntheticBadge } from "@/components/research/badges";
import { Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useCandidates } from "@/hooks/use-research";
import { useDebounce } from "@/hooks/use-debounce";
import { ApiError } from "@/lib/api";
import { formatPercent, formatPrice, pnlClass } from "@/lib/format";
import { formatMultiple, formatPct, formatScore, istStamp, reportHref } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { CandidateRead, CandidatesQuery, ResearchDirection, ResearchSortKey } from "@/types/research";

const ALL = "__all__";

interface Filters {
  minScore: string;
  minConfidence: string;
  minRelVolume: string;
  minPrice: string;
  maxPrice: string;
  sector: string;
  risk: string;
  direction: string;
}
const NO_FILTERS: Filters = {
  minScore: "",
  minConfidence: "",
  minRelVolume: "",
  minPrice: "",
  maxPrice: "",
  sector: ALL,
  risk: ALL,
  direction: ALL,
};

const RISK_OPTIONS: SelectOption[] = [
  { value: ALL, label: "Any risk" },
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
];
const DIRECTION_OPTIONS: SelectOption[] = [
  { value: ALL, label: "Any direction" },
  { value: "BULLISH", label: "Bullish" },
  { value: "BEARISH", label: "Bearish" },
  { value: "NEUTRAL", label: "Neutral" },
];

function toQuery(f: Filters, sort: ResearchSortKey, order: "asc" | "desc", unanalysed: boolean): CandidatesQuery {
  const q: CandidatesQuery = { sort, order, limit: 200, include_unanalyzed: unanalysed || undefined };
  const num = (s: string) => parseNumber(s);
  const set = <K extends keyof CandidatesQuery>(key: K, value: CandidatesQuery[K] | null) => {
    if (value !== null && value !== undefined) q[key] = value;
  };
  set("min_score", num(f.minScore));
  set("min_confidence", num(f.minConfidence));
  set("min_rel_volume", num(f.minRelVolume));
  set("min_price", num(f.minPrice));
  set("max_price", num(f.maxPrice));
  if (f.sector !== ALL) q.sector = f.sector;
  if (f.risk !== ALL) q.risk = f.risk as CandidatesQuery["risk"];
  if (f.direction !== ALL) q.direction = f.direction as ResearchDirection;
  return q;
}

function SortHeader({
  label,
  sortKey,
  sort,
  order,
  onSort,
  align = "left",
}: {
  label: string;
  sortKey: ResearchSortKey;
  sort: ResearchSortKey;
  order: "asc" | "desc";
  onSort: (key: ResearchSortKey) => void;
  align?: "left" | "right";
}) {
  const active = sort === sortKey;
  const Icon = !active ? ArrowUpDown : order === "desc" ? ArrowDown : ArrowUp;
  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      aria-label={`Sort by ${label}${active ? `, currently ${order === "desc" ? "descending" : "ascending"}` : ""}`}
      className={cn(
        "inline-flex items-center gap-1 uppercase hover:text-foreground",
        align === "right" && "flex-row-reverse",
        active && "text-foreground",
      )}
    >
      {label}
      <Icon className={cn("size-3", !active && "opacity-50")} aria-hidden />
    </button>
  );
}

function ScoreCell({ c }: { c: CandidateRead }) {
  if (c.research_score === null) {
    return <span className="text-muted-foreground">{c.stage === "ANALYZED" ? "Not assessed" : "—"}</span>;
  }
  return (
    <div
      className="ml-auto flex w-20 flex-col items-end gap-1"
      title={`Covers ${formatPct(c.coverage_pct, 0)} of scoring weights`}
    >
      <span className="tabular font-semibold">{formatScore(c.research_score)}</span>
      <span className="h-1 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
        <span className="block h-full rounded-full bg-info" style={{ width: `${Math.min(100, c.research_score)}%` }} />
      </span>
    </div>
  );
}

interface CandidatesSectionProps {
  onStartScan?: () => void;
  scanActive?: boolean;
  /** Show the candidates of one specific run (History page) instead of the latest completed run. */
  runId?: string;
  title?: string;
}

export function CandidatesSection({ onStartScan, scanActive = false, runId, title }: CandidatesSectionProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [sort, setSort] = useState<ResearchSortKey>("score");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [unanalysed, setUnanalysed] = useState(false);

  const debouncedFilters = useDebounce(JSON.stringify(filters), 350);
  const query = useMemo(
    () => ({
      ...toQuery(JSON.parse(debouncedFilters) as Filters, sort, order, unanalysed),
      ...(runId ? { run_id: runId } : {}),
    }),
    [debouncedFilters, sort, order, unanalysed, runId],
  );
  const { data, isLoading, error, refetch, isFetching } = useCandidates(query);

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters((f) => ({ ...f, [key]: value }));
  const filtered = JSON.stringify(filters) !== JSON.stringify(NO_FILTERS);
  const onSort = (key: ResearchSortKey) => {
    if (key === sort) setOrder((o) => (o === "desc" ? "asc" : "desc"));
    else {
      setSort(key);
      setOrder(key === "symbol" ? "asc" : "desc");
    }
  };

  const sectorOptions: SelectOption[] = [
    { value: ALL, label: "Any sector" },
    ...(data?.sectors ?? []).map((s) => ({ value: s, label: s })),
  ];
  const head = (label: string, key: ResearchSortKey, align: "left" | "right" = "right") => (
    <SortHeader label={label} sortKey={key} sort={sort} order={order} onSort={onSort} align={align} />
  );
  const isAnalysed = (c: CandidateRead) => c.stage === "ANALYZED";

  const columns: Column<CandidateRead>[] = [
    {
      key: "rank",
      header: "Rank",
      cell: (c) => <span className="tabular text-muted-foreground">{c.rank ?? "—"}</span>,
    },
    {
      key: "symbol",
      header: head("Symbol", "symbol", "left"),
      cell: (c) => (
        <div className="min-w-0">
          <span className="font-medium">{c.symbol}</span>
          {!isAnalysed(c) ? (
            <>
              {" "}
              <Pill>Not analysed</Pill>
              <p className="mt-0.5 max-w-64 text-xs whitespace-normal text-muted-foreground">
                {c.exclusion_reason ?? "Excluded before analysis"}
              </p>
            </>
          ) : null}
        </div>
      ),
    },
    {
      key: "company",
      header: "Company",
      hideBelow: "md",
      cell: (c) => (
        <span className="block max-w-28 truncate" title={c.company}>
          {c.company}
        </span>
      ),
    },
    { key: "price", header: head("Price", "price"), align: "right", cell: (c) => formatPrice(c.price) },
    {
      key: "change",
      header: head("Change %", "change"),
      align: "right",
      cell: (c) => (
        <span className={cn("tabular font-medium", pnlClass(c.change_pct))}>
          {formatPercent(c.change_pct, 2, true)}
        </span>
      ),
    },
    {
      key: "rvol",
      header: head("Rel. volume", "rel_volume"),
      align: "right",
      hideBelow: "sm",
      cell: (c) => formatMultiple(c.rel_volume),
    },
    { key: "atr", header: head("ATR %", "atr"), align: "right", hideBelow: "md", cell: (c) => formatPct(c.atr_pct, 2) },
    {
      key: "vwap",
      header: "VWAP",
      hideBelow: "lg",
      cell: (c) =>
        c.vwap_position ? (
          <span
            className={cn(
              "text-xs font-medium",
              c.vwap_position === "ABOVE"
                ? "text-profit"
                : c.vwap_position === "BELOW"
                  ? "text-loss"
                  : "text-muted-foreground",
            )}
          >
            {c.vwap_position.charAt(0) + c.vwap_position.slice(1).toLowerCase()}
          </span>
        ) : (
          "—"
        ),
    },
    { key: "sector", header: "Sector", hideBelow: "xl", cell: (c) => c.sector ?? "—" },
    { key: "score", header: head("Research Score", "score"), align: "right", cell: (c) => <ScoreCell c={c} /> },
    {
      key: "conf",
      header: head("Confidence", "confidence"),
      align: "right",
      cell: (c) => <span className="tabular">{formatScore(c.data_confidence)}</span>,
    },
    {
      key: "risk",
      header: "Risk",
      hideBelow: "sm",
      cell: (c) => (c.risk_level ? <RiskBadge level={c.risk_level} /> : "—"),
    },
    {
      key: "catalyst",
      header: "Catalyst",
      hideBelow: "xl",
      cell: (c) => <span className="text-xs text-muted-foreground">{c.catalyst || "Not assessed"}</span>,
    },
  ];

  const noRunYet = error instanceof ApiError && error.code === 404;
  const run = data?.run ?? null;

  return (
    <section aria-label="Top Research Candidates" className="grid gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">{title ?? "Top Research Candidates"}</h2>
          <p className="text-xs text-muted-foreground">
            {run ? (
              <>
                Run #{run.run_number} · {istStamp(run.as_of)} · {run.universe} · {run.depth.toLowerCase()} ·{" "}
                {run.candidates_analyzed} analysed of {run.candidates_scanned} scanned
                {data ? ` · showing ${data.items.length} of ${data.total}` : ""}
              </>
            ) : (
              "Ranked by Research Score, an explicit-rule rating of the setup. It is not a recommendation."
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">{run?.is_synthetic ? <SyntheticBadge /> : null}</div>
      </div>

      {!noRunYet ? (
        <div className="grid gap-2.5 rounded-lg border bg-card p-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
            <Field label="Min score" htmlFor="f-score">
              <Input
                id="f-score"
                type="number"
                min={0}
                max={100}
                inputMode="decimal"
                value={filters.minScore}
                onChange={(e) => set("minScore", e.target.value)}
                placeholder="0-100"
              />
            </Field>
            <Field label="Min confidence" htmlFor="f-conf">
              <Input
                id="f-conf"
                type="number"
                min={0}
                max={100}
                inputMode="decimal"
                value={filters.minConfidence}
                onChange={(e) => set("minConfidence", e.target.value)}
                placeholder="0-100"
              />
            </Field>
            <Field label="Min rel. volume" htmlFor="f-rvol">
              <Input
                id="f-rvol"
                type="number"
                min={0}
                step="0.1"
                inputMode="decimal"
                value={filters.minRelVolume}
                onChange={(e) => set("minRelVolume", e.target.value)}
                placeholder="e.g. 1.5"
              />
            </Field>
            <Field label="Min price (₹)" htmlFor="f-minp">
              <Input
                id="f-minp"
                type="number"
                min={0}
                inputMode="decimal"
                value={filters.minPrice}
                onChange={(e) => set("minPrice", e.target.value)}
              />
            </Field>
            <Field label="Max price (₹)" htmlFor="f-maxp">
              <Input
                id="f-maxp"
                type="number"
                min={0}
                inputMode="decimal"
                value={filters.maxPrice}
                onChange={(e) => set("maxPrice", e.target.value)}
              />
            </Field>
            <Field label="Sector" htmlFor="f-sector">
              <SimpleSelect
                id="f-sector"
                value={filters.sector}
                onChange={(v) => set("sector", v)}
                options={sectorOptions}
              />
            </Field>
            <Field label="Risk" htmlFor="f-risk">
              <SimpleSelect id="f-risk" value={filters.risk} onChange={(v) => set("risk", v)} options={RISK_OPTIONS} />
            </Field>
            <Field label="Direction" htmlFor="f-dir">
              <SimpleSelect
                id="f-dir"
                value={filters.direction}
                onChange={(v) => set("direction", v)}
                options={DIRECTION_OPTIONS}
              />
            </Field>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="flex items-center gap-2">
              <Switch id="f-unanalysed" size="sm" checked={unanalysed} onCheckedChange={(c) => setUnanalysed(c)} />
              <Label htmlFor="f-unanalysed" className="text-xs">
                Show stocks that were scanned but not analysed
              </Label>
            </div>
            {filtered ? (
              <Button variant="ghost" size="xs" onClick={() => setFilters(NO_FILTERS)}>
                <X /> Clear filters
              </Button>
            ) : null}
            {isFetching && data ? <span className="text-xs text-muted-foreground">Updating…</span> : null}
          </div>
        </div>
      ) : null}

      {error && !data && !noRunYet ? (
        <div className="rounded-lg border bg-card">
          <ErrorState error={error} onRetry={() => void refetch()} />
        </div>
      ) : noRunYet || (!isLoading && data && data.run === null) ? (
        <div className="rounded-lg border bg-card">
          <EmptyState
            title="No research candidates yet"
            description="Research candidates appear after a scan. Choose New Research Scan, pick a universe such as NIFTY50 and a depth, and start. Each agent's progress is shown while the scan runs."
            action={
              onStartScan ? (
                <Button onClick={onStartScan} disabled={scanActive}>
                  <Play /> New Research Scan
                </Button>
              ) : undefined
            }
          />
        </div>
      ) : (
        <DataTable
          className="[&_td]:px-1.5 [&_th]:px-1.5"
          columns={columns}
          rows={data?.items}
          rowKey={(c) => `${c.run_id}:${c.symbol}`}
          isLoading={isLoading}
          error={error}
          onRetry={() => void refetch()}
          skeletonRows={8}
          onRowClick={(c) => {
            if (isAnalysed(c)) router.push(reportHref(c.symbol, runId));
          }}
          rowClassName={(c) => (isAnalysed(c) ? undefined : "opacity-70 cursor-default")}
          emptyTitle={filtered ? "No candidates match these filters" : "This run has no analysed candidates"}
          emptyDescription={
            filtered
              ? "Loosen a filter, or clear them all."
              : "Turn on “Show stocks that were scanned but not analysed” to see why stocks were excluded."
          }
        />
      )}
      {!runId ? (
        <p className="text-xs text-muted-foreground">
          Planned, not built yet: news and catalyst analysis, corporate events, and fundamentals. Until they are
          connected the Catalyst column reads &quot;Not assessed&quot; and the score does not cover them.
        </p>
      ) : null}
    </section>
  );
}
