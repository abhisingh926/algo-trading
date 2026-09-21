"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, FlaskConical, Loader2, Play, Save } from "lucide-react";
import { Field, parseNumber, SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { InstrumentCombobox } from "@/components/trading/instrument-combobox";
import { StartStrategyDialog } from "@/components/trading/start-strategy-dialog";
import { StrategyReviewPanel } from "@/components/trading/strategy-review-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useBrokers } from "@/hooks/use-brokers";
import { useDebounce } from "@/hooks/use-debounce";
import { useDraftReview } from "@/hooks/use-guide";
import { useCreateStrategy, useUpdateStrategy } from "@/hooks/use-strategies";
import { ApiError } from "@/lib/api";
import { fractionToPercent, percentToFraction } from "@/lib/format";
import { toastSuccess } from "@/lib/toast";
import type {
  ReviewRequest,
  Strategy,
  StrategyCreate,
  StrategyParameterInfo,
  StrategyType,
  StrategyTypeInfo,
  Timeframe,
  TradingMode,
} from "@/types";

export const TIMEFRAME_OPTIONS: SelectOption<Timeframe>[] = [
  { value: "1m", label: "1 minute" },
  { value: "5m", label: "5 minutes" },
  { value: "15m", label: "15 minutes" },
  { value: "1h", label: "1 hour" },
  { value: "1d", label: "1 day" },
];
const MODE_OPTIONS: SelectOption<TradingMode>[] = [
  { value: "PAPER", label: "PAPER (simulated fills)" },
  { value: "SANDBOX", label: "SANDBOX (broker sandbox)" },
  { value: "LIVE", label: "LIVE (real money)" },
];
const NO_BROKER = "__default__";

interface FormState {
  name: string;
  strategy_type: StrategyType | "";
  symbol: string;
  exchange: string;
  timeframe: Timeframe;
  capital: string;
  risk_pct: string;
  stop_loss_pct: string;
  target_pct: string;
  allow_short: boolean;
  trading_mode: TradingMode;
  broker_account_id: string;
  parameters: Record<string, string>;
}

const str = (n: number | null | undefined) => (n === null || n === undefined ? "" : String(n));

function defaultParams(info: StrategyTypeInfo | undefined): Record<string, string> {
  return Object.fromEntries((info?.parameters ?? []).map((p) => [p.key, String(p.default)]));
}

function initialState(types: StrategyTypeInfo[], strategy?: Strategy): FormState {
  if (strategy) {
    const info = types.find((t) => t.type === strategy.strategy_type);
    return {
      name: strategy.name,
      strategy_type: strategy.strategy_type,
      symbol: strategy.symbol,
      exchange: strategy.exchange,
      timeframe: strategy.timeframe,
      capital: str(strategy.capital),
      risk_pct: str(fractionToPercent(strategy.risk_per_trade)),
      stop_loss_pct: str(fractionToPercent(strategy.stop_loss_pct)),
      target_pct: str(fractionToPercent(strategy.target_pct)),
      allow_short: strategy.allow_short,
      trading_mode: strategy.trading_mode,
      broker_account_id: strategy.broker_account_id ?? NO_BROKER,
      parameters: {
        ...defaultParams(info),
        ...Object.fromEntries(Object.entries(strategy.parameters).map(([k, v]) => [k, String(v)])),
      },
    };
  }
  const first = types[0];
  return {
    name: "",
    strategy_type: first?.type ?? "",
    symbol: "",
    exchange: "NSE",
    timeframe: "5m",
    capital: "100000",
    risk_pct: "1",
    stop_loss_pct: "1",
    target_pct: "2",
    allow_short: false,
    trading_mode: "PAPER",
    broker_account_id: NO_BROKER,
    parameters: defaultParams(first),
  };
}

function validateParam(p: StrategyParameterInfo, raw: string): string | undefined {
  const n = parseNumber(raw);
  if (n === null) return "Required";
  if (p.type === "int" && !Number.isInteger(n)) return "Must be a whole number";
  if (n < p.min || n > p.max) return `Must be between ${p.min} and ${p.max}`;
  return undefined;
}

type Errors = Record<string, string>;

/**
 * Pure validation of the form. `payload` is built whenever everything except the name is valid, so the
 * good-practice review can run before the user has typed a name; saving still requires `errors` to be empty.
 */
function evaluateForm(
  form: FormState,
  typeInfo: StrategyTypeInfo | undefined,
): { errors: Errors; payload: StrategyCreate | null } {
  const e: Errors = {};
  if (!form.name.trim()) e.name = "Strategy name is required";
  if (!form.strategy_type) e.strategy_type = "Select a strategy type";
  if (!form.symbol) e.symbol = "Select a symbol";

  const capital = parseNumber(form.capital);
  if (capital === null || capital <= 0) e.capital = "Capital must be greater than 0";
  const risk = parseNumber(form.risk_pct);
  if (risk === null || risk <= 0 || risk > 100) e.risk_pct = "Enter a percent between 0 and 100";
  const sl = parseNumber(form.stop_loss_pct);
  if (sl === null || sl <= 0 || sl >= 100) e.stop_loss_pct = "Enter a percent above 0 and below 100";
  const targetRaw = form.target_pct.trim();
  const target = parseNumber(form.target_pct);
  if (targetRaw !== "" && (target === null || target <= 0)) e.target_pct = "Enter a positive percent or leave blank";

  const parameters: Record<string, number> = {};
  for (const p of typeInfo?.parameters ?? []) {
    const raw = form.parameters[p.key] ?? "";
    const err = validateParam(p, raw);
    if (err) e[`parameters.${p.key}`] = err;
    else parameters[p.key] = Number(raw);
  }

  const blocking = Object.keys(e).some((k) => k !== "name");
  if (blocking || !form.strategy_type || capital === null || risk === null || sl === null) {
    return { errors: e, payload: null };
  }
  return {
    errors: e,
    payload: {
      name: form.name.trim(),
      strategy_type: form.strategy_type,
      symbol: form.symbol,
      exchange: form.exchange,
      timeframe: form.timeframe,
      capital,
      risk_per_trade: percentToFraction(risk),
      stop_loss_pct: percentToFraction(sl),
      target_pct: target === null ? null : percentToFraction(target),
      allow_short: form.allow_short,
      trading_mode: form.trading_mode,
      broker_account_id: form.broker_account_id === NO_BROKER ? null : form.broker_account_id,
      parameters,
    },
  };
}

type Intent = "save" | "backtest" | "start";

interface StrategyFormProps {
  types: StrategyTypeInfo[];
  /** Present when editing. */
  strategy?: Strategy;
}

export function StrategyForm({ types, strategy }: StrategyFormProps) {
  const router = useRouter();
  const brokers = useBrokers();
  const create = useCreateStrategy();
  const update = useUpdateStrategy();

  const [form, setForm] = useState<FormState>(() => initialState(types, strategy));
  const [errors, setErrors] = useState<Errors>({});
  const [savedId, setSavedId] = useState<string | null>(strategy?.id ?? null);
  const [intent, setIntent] = useState<Intent | null>(null);
  const [toStart, setToStart] = useState<Strategy | null>(null);

  const typeInfo = types.find((t) => t.type === form.strategy_type);
  const running = strategy?.status === "RUNNING";
  const pending = create.isPending || update.isPending;

  // Good-practice review of the current (unsaved) form values: debounced, advisory, never blocks saving.
  const reviewKey = useMemo(() => {
    const { payload } = evaluateForm(form, typeInfo);
    if (!payload) return null;
    const request: ReviewRequest = {
      ...(savedId ? { strategy_id: savedId } : {}),
      strategy_type: payload.strategy_type,
      symbol: payload.symbol,
      exchange: payload.exchange,
      timeframe: payload.timeframe,
      capital: payload.capital,
      risk_per_trade: payload.risk_per_trade,
      stop_loss_pct: payload.stop_loss_pct,
      target_pct: payload.target_pct,
      allow_short: payload.allow_short,
      trading_mode: payload.trading_mode,
      parameters: payload.parameters,
    };
    return JSON.stringify(request);
  }, [form, typeInfo, savedId]);
  const debouncedKey = useDebounce(reviewKey, 600);
  const reviewRequest = useMemo(
    () => (debouncedKey ? (JSON.parse(debouncedKey) as ReviewRequest) : null),
    [debouncedKey],
  );
  const draftReview = useDraftReview(reviewRequest);
  const reviewIdle = reviewKey === null;

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));

  const brokerOptions: SelectOption[] = [
    { value: NO_BROKER, label: "System default" },
    ...(brokers.data ?? [])
      .filter((b) => b.is_active || b.id === form.broker_account_id)
      .map((b) => ({ value: b.id, label: `${b.name} (${b.broker_type} · ${b.environment})` })),
  ];

  function buildPayload(): StrategyCreate | null {
    const { errors: e, payload } = evaluateForm(form, typeInfo);
    setErrors(e);
    return Object.keys(e).length === 0 ? payload : null;
  }

  async function submit(next: Intent) {
    const payload = buildPayload();
    if (!payload) return;
    setIntent(next);
    try {
      const saved = savedId
        ? await update.mutateAsync({ id: savedId, body: payload })
        : await create.mutateAsync(payload);
      setSavedId(saved.id);
      toastSuccess(strategy || savedId ? "Strategy saved" : "Strategy created", saved.name);
      if (next === "save") router.push("/strategies");
      else if (next === "backtest") router.push(`/backtesting?strategy_id=${encodeURIComponent(saved.id)}`);
      else setToStart(saved);
    } catch (err) {
      // The mutation hooks already toast; map 422 field errors onto the form.
      if (err instanceof ApiError) {
        const map: Record<string, string> = {
          risk_per_trade: "risk_pct",
          stop_loss_pct: "stop_loss_pct",
          target_pct: "target_pct",
        };
        const fe = Object.fromEntries(err.fieldErrors.map((x) => [map[x.field] ?? x.field, x.message]));
        if (Object.keys(fe).length > 0) setErrors(fe);
      }
    } finally {
      setIntent(null);
    }
  }

  const spinner = (i: Intent, icon: React.ReactNode) =>
    pending && intent === i ? <Loader2 className="animate-spin" /> : icon;

  return (
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,52rem)_minmax(20rem,26rem)]">
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void submit("save");
        }}
        className="grid min-w-0 gap-6"
      >
        {running ? (
          <p className="flex gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            This strategy is RUNNING. Stop it before editing: the backend rejects changes to running strategies.
          </p>
        ) : null}

        <fieldset disabled={running || pending} className="grid gap-6">
          <FormSection title="Strategy">
            <Field label="Strategy Name" htmlFor="name" error={errors.name}>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. RELIANCE EMA 9/21"
                aria-invalid={!!errors.name}
                maxLength={120}
              />
            </Field>
            <Field label="Strategy" htmlFor="strategy_type" error={errors.strategy_type} hint={typeInfo?.description}>
              <SimpleSelect
                id="strategy_type"
                value={form.strategy_type}
                onChange={(v) => {
                  const info = types.find((t) => t.type === v);
                  setForm((f) => ({ ...f, strategy_type: v, parameters: defaultParams(info) }));
                }}
                options={types.map((t) => ({ value: t.type, label: t.name }))}
                invalid={!!errors.strategy_type}
              />
            </Field>
            {(typeInfo?.parameters ?? []).map((p) => (
              <Field
                key={p.key}
                label={p.label}
                htmlFor={`param-${p.key}`}
                error={errors[`parameters.${p.key}`]}
                hint={`${p.description} (${p.min} to ${p.max}, default ${p.default})`}
              >
                <Input
                  id={`param-${p.key}`}
                  type="number"
                  inputMode={p.type === "int" ? "numeric" : "decimal"}
                  step={p.type === "int" ? 1 : "any"}
                  min={p.min}
                  max={p.max}
                  value={form.parameters[p.key] ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, parameters: { ...f.parameters, [p.key]: e.target.value } }))}
                  aria-invalid={!!errors[`parameters.${p.key}`]}
                />
              </Field>
            ))}
          </FormSection>

          <FormSection title="Market">
            <Field label="Symbol" htmlFor="symbol" error={errors.symbol}>
              <InstrumentCombobox
                id="symbol"
                symbol={form.symbol}
                exchange={form.exchange}
                onSelect={(i) => setForm((f) => ({ ...f, symbol: i.symbol, exchange: i.exchange }))}
                invalid={!!errors.symbol}
                disabled={running || pending}
              />
            </Field>
            <Field label="Timeframe" htmlFor="timeframe">
              <SimpleSelect
                id="timeframe"
                value={form.timeframe}
                onChange={(v) => set("timeframe", v)}
                options={TIMEFRAME_OPTIONS}
              />
            </Field>
          </FormSection>

          <FormSection title="Capital & risk">
            <Field label="Capital (₹)" htmlFor="capital" error={errors.capital}>
              <Input
                id="capital"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                value={form.capital}
                onChange={(e) => set("capital", e.target.value)}
                aria-invalid={!!errors.capital}
              />
            </Field>
            <Field
              label="Risk per trade (%)"
              htmlFor="risk_pct"
              error={errors.risk_pct}
              hint="Percent of capital risked on each trade"
            >
              <Input
                id="risk_pct"
                type="number"
                inputMode="decimal"
                min={0}
                max={100}
                step="any"
                value={form.risk_pct}
                onChange={(e) => set("risk_pct", e.target.value)}
                aria-invalid={!!errors.risk_pct}
              />
            </Field>
            <Field label="Stop Loss (%)" htmlFor="stop_loss_pct" error={errors.stop_loss_pct}>
              <Input
                id="stop_loss_pct"
                type="number"
                inputMode="decimal"
                min={0}
                max={100}
                step="any"
                value={form.stop_loss_pct}
                onChange={(e) => set("stop_loss_pct", e.target.value)}
                aria-invalid={!!errors.stop_loss_pct}
              />
            </Field>
            <Field label="Target (%)" htmlFor="target_pct" error={errors.target_pct} hint="Leave blank for no target">
              <Input
                id="target_pct"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                value={form.target_pct}
                onChange={(e) => set("target_pct", e.target.value)}
                aria-invalid={!!errors.target_pct}
              />
            </Field>
            <div className="flex items-center gap-2.5 sm:col-span-2">
              <Switch id="allow_short" checked={form.allow_short} onCheckedChange={(c) => set("allow_short", c)} />
              <Label htmlFor="allow_short">Allow short selling</Label>
            </div>
          </FormSection>

          <FormSection title="Execution">
            <Field label="Trading Mode" htmlFor="trading_mode">
              <SimpleSelect
                id="trading_mode"
                value={form.trading_mode}
                onChange={(v) => set("trading_mode", v)}
                options={MODE_OPTIONS}
              />
            </Field>
            <Field
              label="Broker account"
              htmlFor="broker_account_id"
              hint={
                brokers.error
                  ? "Could not load broker accounts"
                  : "Credentials are configured on the backend, never here"
              }
            >
              <SimpleSelect
                id="broker_account_id"
                value={form.broker_account_id}
                onChange={(v) => set("broker_account_id", v)}
                options={brokerOptions}
              />
            </Field>
            {form.trading_mode === "LIVE" ? (
              <p className="flex gap-2 rounded-md border border-loss/40 bg-loss/10 p-3 text-sm text-loss sm:col-span-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <span>
                  <strong>LIVE mode trades real money.</strong> Orders go to the real exchange through your broker.
                  Backtest and paper trade this strategy first. Live orders are only accepted when every backend
                  live-trading guard passes (see the Brokers page).
                </span>
              </p>
            ) : null}
          </FormSection>
        </fieldset>

        <div className="flex flex-wrap items-center gap-2 border-t pt-4">
          <Button type="submit" disabled={running || pending}>
            {spinner("save", <Save />)} Save
          </Button>
          <Button type="button" variant="outline" disabled={running || pending} onClick={() => void submit("backtest")}>
            {spinner("backtest", <FlaskConical />)} Backtest
          </Button>
          <Button type="button" variant="outline" disabled={running || pending} onClick={() => void submit("start")}>
            {spinner("start", <Play />)} Save &amp; Start
          </Button>
          <Link href="/strategies" className={buttonVariants({ variant: "ghost" })}>
            Cancel
          </Link>
        </div>
      </form>

      <aside className="min-w-0 xl:sticky xl:top-20">
        <StrategyReviewPanel
          title="Good-practice review"
          review={reviewIdle ? undefined : draftReview.data}
          isLoading={!reviewIdle && !draftReview.data && !draftReview.error}
          isFetching={!reviewIdle && (reviewKey !== debouncedKey || draftReview.isFetching)}
          error={reviewIdle ? undefined : draftReview.error}
          onRetry={() => void draftReview.refetch()}
          placeholder="Choose a strategy, symbol, capital, risk and stop loss to see a review of this setup. It is advisory and never blocks saving."
        />
      </aside>

      <StartStrategyDialog
        strategy={toStart}
        onOpenChange={(o) => {
          if (!o) setToStart(null);
        }}
        onStarted={() => router.push("/strategies")}
      />
    </div>
  );
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="grid gap-4 rounded-lg border bg-card p-4 sm:grid-cols-2">{children}</div>
    </section>
  );
}
