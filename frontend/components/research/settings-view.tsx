"use client";

import { useState } from "react";
import { Check, Loader2, RotateCcw, ShieldCheck } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { Field, parseNumber, SimpleSelect } from "@/components/layout/form-controls";
import { PageHeader, Section } from "@/components/layout/page-header";
import { ProgressBar } from "@/components/layout/progress-bar";
import { ResearchDisclaimer } from "@/components/research/disclaimer";
import { DataTable, type Column } from "@/components/tables/data-table";
import { ErrorState } from "@/components/tables/states";
import { Pill } from "@/components/trading/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useApproveWeights,
  useProposeWeights,
  useSourceRegistry,
  useUniverse,
  useUniverses,
  useUpdateSource,
  useWeights,
} from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { formatUnit, SOURCE_TYPE_TEXT } from "@/lib/research";
import { errorText } from "@/lib/toast";
import { cn } from "@/lib/utils";
import type { SourceRegistryRead, UniverseMemberRead, WeightKey, WeightSetRead } from "@/types/research";

const WEIGHT_LABELS: Record<WeightKey, string> = {
  market_regime: "Market Regime",
  liquidity: "Liquidity",
  price_action: "Price Action",
  momentum: "Momentum",
  volume: "Volume",
  volatility: "Volatility",
  technical_setup: "Technical Setup",
  news_catalyst: "News / Catalyst",
  historical_setup: "Historical Setup",
  risk: "Risk",
};
const WEIGHT_KEYS = Object.keys(WEIGHT_LABELS) as WeightKey[];
const weightLabel = (k: string) =>
  (WEIGHT_LABELS as Record<string, string>)[k] ?? k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const sum = (w: Record<string, number>) => Object.values(w).reduce((s, v) => s + v, 0);
const TOTAL = 100;
const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;

// ---------- scoring weights ----------
function ActiveWeights({ set }: { set: WeightSetRead }) {
  const entries = Object.entries(set.weights);
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 className="text-sm font-semibold">
          {set.name} · v{set.version}
        </h3>
        <Pill tone="good" dot>
          Active
        </Pill>
        <span className="text-xs text-muted-foreground">
          Approved {set.approved_at ? `${formatDateTime(set.approved_at)} IST` : "—"}
          {set.approved_by ? ` by ${set.approved_by}` : ""}
        </span>
      </div>
      {set.notes ? <p className="mt-1 text-xs text-muted-foreground">{set.notes}</p> : null}
      <ul className="mt-3 grid gap-x-8 gap-y-2.5 md:grid-cols-2">
        {entries.map(([k, v]) => (
          <li key={k}>
            <p className="flex items-baseline justify-between text-sm">
              <span>{weightLabel(k)}</span>
              <span className="tabular font-medium">{v} points</span>
            </p>
            <ProgressBar value={(v / TOTAL) * 100} label={weightLabel(k)} barClassName="bg-info" className="mt-1" />
          </li>
        ))}
      </ul>
      <p className="tabular mt-3 text-xs text-muted-foreground">
        Total {sum(set.weights)} points. News / Catalyst counts towards the total but is shown as &quot;Not
        assessed&quot; until a news source is connected.
      </p>
    </div>
  );
}

function ProposeForm({ active }: { active: WeightSetRead | null }) {
  const propose = useProposeWeights();
  const initial = (): Record<string, string> =>
    Object.fromEntries(WEIGHT_KEYS.map((k) => [k, String(active?.weights[k] ?? 0)]));
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const nums = WEIGHT_KEYS.map((k) => parseNumber(values[k]));
  const total = nums.reduce<number>((s, n) => s + (n ?? 0), 0);
  const totalOk = near(total, TOTAL);
  const diff = Math.round((total - TOTAL) * 1e6) / 1e6;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = "Give the proposal a name";
    const weights: Record<string, number> = {};
    WEIGHT_KEYS.forEach((k, i) => {
      const n = nums[i];
      if (n === null) errs[k] = "Enter a number";
      else if (n < 0) errs[k] = "Cannot be negative";
      else if (n > TOTAL) errs[k] = "Cannot exceed 100";
      else weights[k] = n;
    });
    if (!totalOk) errs.total = `The weights must add up to exactly ${TOTAL} (now ${Math.round(total * 100) / 100})`;
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    propose.mutate(
      { name: name.trim(), weights, notes: notes.trim() || null },
      {
        onSuccess: () => {
          setName("");
          setNotes("");
        },
        onError: (err) => {
          if (err instanceof ApiError) setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field, x.message])));
        },
      },
    );
  }

  return (
    <form onSubmit={submit} noValidate className="rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold">Propose a new weight set</h3>
      <p className="text-xs text-muted-foreground">
        A proposal changes nothing until an administrator approves it. Only approval changes how research is scored.
      </p>
      <fieldset disabled={propose.isPending} className="mt-3 grid gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" htmlFor="w-name" error={errors.name}>
            <Input
              id="w-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              placeholder="e.g. Higher liquidity weight"
              aria-invalid={!!errors.name}
            />
          </Field>
          <Field label="Notes (optional)" htmlFor="w-notes">
            <Textarea id="w-notes" rows={1} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={1000} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {WEIGHT_KEYS.map((k) => (
            <Field key={k} label={weightLabel(k)} htmlFor={`w-${k}`} error={errors[k]}>
              <Input
                id={`w-${k}`}
                type="number"
                inputMode="decimal"
                min={0}
                max={TOTAL}
                step="any"
                value={values[k]}
                onChange={(e) => setValues((v) => ({ ...v, [k]: e.target.value }))}
                aria-invalid={!!errors[k]}
              />
            </Field>
          ))}
        </div>
        <div
          role="status"
          className={cn(
            "flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm",
            totalOk ? "border-profit/40 bg-profit/10 text-profit" : "border-warning/40 bg-warning/10 text-warning",
          )}
        >
          {totalOk ? <Check className="size-4" aria-hidden /> : null}
          <span className="tabular font-semibold">
            Total {Math.round(total * 100) / 100} / {TOTAL}
          </span>
          <span>
            {totalOk
              ? "Adds up to 100."
              : `${diff > 0 ? "Over" : "Under"} by ${Math.abs(Math.round(diff * 100) / 100)}. The weights must add up to exactly 100.`}
          </span>
        </div>
        {errors.total && totalOk === false ? <p className="text-xs text-destructive">{errors.total}</p> : null}
      </fieldset>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-4">
        <Button type="submit" disabled={propose.isPending || !totalOk || !name.trim()}>
          {propose.isPending ? <Loader2 className="animate-spin" /> : null} Propose weights
        </Button>
        <Button type="button" variant="ghost" onClick={() => setValues(initial())}>
          <RotateCcw /> Reset to active
        </Button>
      </div>
    </form>
  );
}

function WeightsSection() {
  const { data, isLoading, error, refetch } = useWeights();
  const approve = useApproveWeights();
  const [toApprove, setToApprove] = useState<WeightSetRead | null>(null);

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  const sets = data ?? [];
  const active = sets.find((s) => s.status === "ACTIVE") ?? null;

  const columns: Column<WeightSetRead>[] = [
    { key: "name", header: "Name", cell: (w) => <span className="font-medium">{w.name}</span> },
    { key: "version", header: "Version", cell: (w) => <span className="tabular">v{w.version}</span> },
    {
      key: "status",
      header: "Status",
      cell: (w) => (
        <Pill tone={w.status === "ACTIVE" ? "good" : w.status === "PROPOSED" ? "warn" : "neutral"} dot>
          {w.status}
        </Pill>
      ),
    },
    {
      key: "weights",
      header: "Weights",
      hideBelow: "lg",
      cell: (w) => (
        <span
          className="block max-w-72 truncate text-xs text-muted-foreground"
          title={Object.entries(w.weights)
            .map(([k, v]) => `${weightLabel(k)} ${v}`)
            .join(", ")}
        >
          {Object.entries(w.weights)
            .map(([k, v]) => `${weightLabel(k)} ${v}`)
            .join(" · ")}
        </span>
      ),
    },
    { key: "created", header: "Created (IST)", hideBelow: "md", cell: (w) => formatDateTime(w.created_at) },
    {
      key: "approved",
      header: "Approved",
      hideBelow: "md",
      cell: (w) =>
        w.approved_at ? `${formatDateTime(w.approved_at)}${w.approved_by ? ` by ${w.approved_by}` : ""}` : "—",
    },
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (w) =>
        w.status === "PROPOSED" ? (
          <Button
            size="xs"
            variant="outline"
            onClick={() => {
              approve.reset();
              setToApprove(w);
            }}
          >
            <ShieldCheck /> Approve
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="grid gap-5">
      {active ? (
        <ActiveWeights set={active} />
      ) : (
        <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">No weight set is active yet.</p>
      )}
      <ProposeForm active={active} />
      <Section title="All weight sets">
        <DataTable
          columns={columns}
          rows={sets}
          rowKey={(w) => w.id}
          isLoading={false}
          error={null}
          emptyTitle="No weight sets"
          skeletonRows={3}
        />
      </Section>
      <ConfirmDialog
        open={!!toApprove}
        onOpenChange={(o) => {
          if (!o) setToApprove(null);
        }}
        title={`Approve "${toApprove?.name ?? ""}" v${toApprove?.version ?? ""}?`}
        description="Approval changes how all future research is scored. The current active set is archived and every new scan will use this set."
        confirmLabel="Approve and activate"
        destructive
        pending={approve.isPending}
        onConfirm={() => toApprove && approve.mutate(toApprove.id, { onSuccess: () => setToApprove(null) })}
      >
        {approve.isError ? (
          <p role="alert" className="rounded-md border border-loss/40 bg-loss/10 p-2.5 text-sm text-loss">
            <strong>{errorText(approve.error).title}.</strong> {errorText(approve.error).description}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">Only an administrator can approve a weight set.</p>
        )}
      </ConfirmDialog>
    </div>
  );
}

// ---------- source registry ----------
function SourceRegistrySection() {
  const { data, isLoading, error, refetch } = useSourceRegistry();
  const update = useUpdateSource();

  const columns: Column<SourceRegistryRead>[] = [
    {
      key: "name",
      header: "Source",
      cell: (s) => (
        <div className="min-w-0">
          <p className="font-medium">{s.name}</p>
          <p className="font-mono text-[11px] text-muted-foreground">{s.key}</p>
        </div>
      ),
    },
    {
      key: "type",
      header: "Type",
      hideBelow: "sm",
      cell: (s) => <Pill>{SOURCE_TYPE_TEXT[s.source_type as keyof typeof SOURCE_TYPE_TEXT] ?? s.source_type}</Pill>,
    },
    { key: "tier", header: "Tier", align: "right", cell: (s) => <span className="tabular">{s.priority}</span> },
    {
      key: "rel",
      header: "Reliability",
      align: "right",
      cell: (s) => <span className="tabular">{formatUnit(s.reliability_score)}</span>,
    },
    {
      key: "enabled",
      header: "Enabled",
      cell: (s) => (
        <Switch
          size="sm"
          checked={s.enabled}
          aria-label={`${s.name} enabled`}
          disabled={update.isPending && update.variables?.id === s.id}
          onCheckedChange={(c) => update.mutate({ id: s.id, body: { enabled: c } })}
        />
      ),
    },
    {
      key: "connected",
      header: "Connected",
      cell: (s) => (
        <Pill tone={s.connected ? "good" : "neutral"} dot>
          {s.connected ? "Connected" : "Not connected"}
        </Pill>
      ),
    },
    {
      key: "notes",
      header: "Notes",
      hideBelow: "lg",
      cell: (s) => (
        <span className="block max-w-80 truncate text-xs text-muted-foreground" title={s.notes ?? undefined}>
          {s.notes ?? "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted-foreground">
        Where research data may come from. Tier 1 is official (exchanges, regulators, filings), tier 2 is reputable
        commercial and news sources, tier 3 is simulated or derived data. Only sources that are enabled and connected
        can supply data. Most real sources have no adapter yet.
      </p>
      <DataTable
        columns={columns}
        rows={data}
        rowKey={(s) => s.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        skeletonRows={6}
        emptyTitle="No sources registered"
      />
    </div>
  );
}

// ---------- universes ----------
function UniverseSection() {
  const universes = useUniverses();
  const [selected, setSelected] = useState<string | null>(null);
  const name = selected ?? universes.data?.[0]?.name ?? null;
  const universe = useUniverse(name);
  const [filter, setFilter] = useState("");

  const members = (universe.data?.members ?? []).filter((m) => {
    const q = filter.trim().toLowerCase();
    return (
      !q ||
      m.symbol.toLowerCase().includes(q) ||
      (m.company ?? "").toLowerCase().includes(q) ||
      (m.sector ?? "").toLowerCase().includes(q)
    );
  });
  const columns: Column<UniverseMemberRead>[] = [
    { key: "symbol", header: "Symbol", cell: (m) => <span className="font-medium">{m.symbol}</span> },
    { key: "company", header: "Company", hideBelow: "sm", cell: (m) => m.company ?? "—" },
    { key: "sector", header: "Sector", cell: (m) => m.sector ?? "—" },
  ];

  return (
    <div className="grid gap-3">
      <p className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
        {universe.data?.note ?? "Universe lists are approximate."} The list is approximate and not versioned: index
        constituents change over time and this list is not updated automatically. Verify it against the exchange before
        relying on it.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {universes.data && universes.data.length > 1 ? (
          <div className="w-56">
            <SimpleSelect
              value={name ?? ""}
              onChange={setSelected}
              options={universes.data.map((u) => ({ value: u.name, label: `${u.name} (${u.count})` }))}
            />
          </div>
        ) : name ? (
          <span className="text-sm font-medium">
            {name}{" "}
            <span className="font-normal text-muted-foreground">
              ({universe.data?.count ?? universes.data?.[0]?.count ?? "…"} stocks)
            </span>
          </span>
        ) : null}
        <Input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter members"
          aria-label="Filter universe members"
          className="w-56"
        />
      </div>
      <DataTable
        columns={columns}
        rows={universes.isLoading ? undefined : universe.data ? members : undefined}
        rowKey={(m) => m.symbol}
        isLoading={universes.isLoading || universe.isLoading}
        error={universes.error ?? universe.error}
        onRetry={() => {
          void universes.refetch();
          void universe.refetch();
        }}
        skeletonRows={8}
        maxHeightClass="max-h-[28rem]"
        emptyTitle={filter ? "No members match" : "This universe has no members"}
      />
    </div>
  );
}

export function ResearchSettingsView() {
  return (
    <>
      <PageHeader
        title="Research Settings"
        description="How research is scored, where its data may come from, and which stocks are scanned."
      />
      <div className="grid gap-5">
        <ResearchDisclaimer />
        <Tabs defaultValue="weights" className="gap-4">
          <div className="overflow-x-auto pb-1">
            <TabsList className="w-max">
              <TabsTrigger value="weights" className="px-3">
                Scoring weights
              </TabsTrigger>
              <TabsTrigger value="sources" className="px-3">
                Source registry
              </TabsTrigger>
              <TabsTrigger value="universe" className="px-3">
                Universe
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="weights">
            <WeightsSection />
          </TabsContent>
          <TabsContent value="sources">
            <SourceRegistrySection />
          </TabsContent>
          <TabsContent value="universe">
            <UniverseSection />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
