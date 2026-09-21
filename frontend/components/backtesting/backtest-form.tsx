"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Play } from "lucide-react";
import { Field, parseNumber, SimpleSelect } from "@/components/layout/form-controls";
import { InstrumentCombobox } from "@/components/trading/instrument-combobox";
import { TIMEFRAME_OPTIONS } from "@/components/trading/strategy-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ErrorState } from "@/components/tables/states";
import { useRunBacktest } from "@/hooks/use-backtests";
import { useStrategies } from "@/hooks/use-strategies";
import { ApiError } from "@/lib/api";
import { formatFraction, humanize, istDateString, percentToFraction } from "@/lib/format";
import type { Backtest, BacktestCreate, Timeframe } from "@/types";

interface BacktestFormProps {
  initialStrategyId: string | null;
  onStrategyChange: (strategyId: string) => void;
  onCompleted: (backtest: Backtest) => void;
}

export function BacktestForm({ initialStrategyId, onStrategyChange, onCompleted }: BacktestFormProps) {
  const strategies = useStrategies(false);
  const run = useRunBacktest();

  const [strategyId, setStrategyId] = useState(initialStrategyId ?? "");
  // null = follow the selected strategy; a value = explicit override by the user.
  const [instrument, setInstrument] = useState<{ symbol: string; exchange: string } | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe | null>(null);
  const [capital, setCapital] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(() => istDateString(-90));
  const [endDate, setEndDate] = useState(() => istDateString(0));
  const [brokerage, setBrokerage] = useState("20");
  const [slippagePct, setSlippagePct] = useState("0.05");
  const [statutory, setStatutory] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const strategy = strategies.data?.find((s) => s.id === strategyId);
  const symbol = instrument?.symbol ?? strategy?.symbol ?? "";
  const exchange = instrument?.exchange ?? strategy?.exchange ?? "NSE";
  const tf: Timeframe = timeframe ?? strategy?.timeframe ?? "5m";
  const capitalValue = capital ?? (strategy ? String(strategy.capital) : "100000");

  if (strategies.isLoading) return <Skeleton className="h-72 w-full" />;
  if (strategies.error && !strategies.data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={strategies.error} onRetry={() => void strategies.refetch()} />
      </div>
    );
  }
  if (strategies.data && strategies.data.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center text-sm">
        <p className="font-medium">No strategies to backtest</p>
        <p className="mt-1 text-muted-foreground">
          Create a strategy first, then come back to test it on historical data.
        </p>
        <Link href="/strategies/new" className="mt-3 inline-block text-primary underline underline-offset-4">
          Create strategy
        </Link>
      </div>
    );
  }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!strategy) errs.strategy_id = "Select a strategy";
    if (!symbol) errs.symbol = "Select a symbol";
    if (!startDate) errs.start_date = "Required";
    if (!endDate) errs.end_date = "Required";
    if (startDate && endDate && startDate >= endDate) errs.end_date = "End date must be after start date";
    const cap = parseNumber(capitalValue);
    if (cap === null || cap <= 0) errs.initial_capital = "Must be greater than 0";
    const brk = parseNumber(brokerage);
    if (brk === null || brk < 0) errs.brokerage_per_order = "Must be 0 or more";
    const slip = parseNumber(slippagePct);
    if (slip === null || slip < 0 || slip > 100) errs.slippage_pct = "Enter a percent between 0 and 100";
    setErrors(errs);
    if (Object.keys(errs).length > 0 || !strategy || cap === null || brk === null || slip === null) return;

    const body: BacktestCreate = {
      name: `${strategy.name} · ${symbol} ${tf} · ${startDate} to ${endDate}`,
      strategy_id: strategy.id,
      symbol,
      exchange,
      timeframe: tf,
      start_date: startDate,
      end_date: endDate,
      initial_capital: cap,
      brokerage_per_order: brk,
      slippage_pct: percentToFraction(slip),
      include_statutory_charges: statutory,
    };
    run.mutate(body, {
      onSuccess: onCompleted,
      onError: (err) => {
        if (err instanceof ApiError) {
          setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field, x.message])));
        }
      },
    });
  };

  return (
    <form onSubmit={onSubmit} noValidate className="rounded-lg border bg-card p-4">
      <fieldset disabled={run.isPending} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field
          label="Strategy"
          htmlFor="bt-strategy"
          error={errors.strategy_id}
          className="sm:col-span-2"
          hint={
            strategy
              ? `${humanize(strategy.strategy_type)} · risk ${formatFraction(strategy.risk_per_trade)} · SL ${formatFraction(strategy.stop_loss_pct)} · target ${formatFraction(strategy.target_pct)}`
              : "Parameters and risk settings are taken from the strategy"
          }
        >
          <SimpleSelect
            id="bt-strategy"
            value={strategy ? strategyId : ""}
            onChange={(v) => {
              setStrategyId(v);
              // Selecting a strategy prefills symbol, timeframe and capital from it.
              setInstrument(null);
              setTimeframe(null);
              setCapital(null);
              onStrategyChange(v);
            }}
            options={(strategies.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
            placeholder="Select a strategy…"
            invalid={!!errors.strategy_id}
          />
        </Field>
        <Field label="Symbol" htmlFor="bt-symbol" error={errors.symbol}>
          <InstrumentCombobox
            id="bt-symbol"
            symbol={symbol}
            exchange={exchange}
            onSelect={setInstrument}
            invalid={!!errors.symbol}
            disabled={run.isPending}
          />
        </Field>
        <Field label="Timeframe" htmlFor="bt-timeframe" error={errors.timeframe}>
          <SimpleSelect id="bt-timeframe" value={tf} onChange={setTimeframe} options={TIMEFRAME_OPTIONS} />
        </Field>
        <Field label="Start Date" htmlFor="bt-start" error={errors.start_date}>
          <Input
            id="bt-start"
            type="date"
            value={startDate}
            max={endDate || undefined}
            onChange={(e) => setStartDate(e.target.value)}
            aria-invalid={!!errors.start_date}
          />
        </Field>
        <Field label="End Date" htmlFor="bt-end" error={errors.end_date}>
          <Input
            id="bt-end"
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(e) => setEndDate(e.target.value)}
            aria-invalid={!!errors.end_date}
          />
        </Field>
        <Field label="Initial Capital (₹)" htmlFor="bt-capital" error={errors.initial_capital}>
          <Input
            id="bt-capital"
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            value={capitalValue}
            onChange={(e) => setCapital(e.target.value)}
            aria-invalid={!!errors.initial_capital}
          />
        </Field>
        <Field label="Brokerage per order (₹)" htmlFor="bt-brokerage" error={errors.brokerage_per_order}>
          <Input
            id="bt-brokerage"
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            value={brokerage}
            onChange={(e) => setBrokerage(e.target.value)}
            aria-invalid={!!errors.brokerage_per_order}
          />
        </Field>
        <Field label="Slippage (%)" htmlFor="bt-slippage" error={errors.slippage_pct} hint="Applied to every fill">
          <Input
            id="bt-slippage"
            type="number"
            inputMode="decimal"
            min={0}
            max={100}
            step="any"
            value={slippagePct}
            onChange={(e) => setSlippagePct(e.target.value)}
            aria-invalid={!!errors.slippage_pct}
          />
        </Field>
        <div className="flex items-center gap-2.5 sm:col-span-2 lg:col-span-2">
          <Switch id="bt-statutory" checked={statutory} onCheckedChange={(c) => setStatutory(c)} />
          <Label htmlFor="bt-statutory" className="leading-snug">
            Include statutory charges (STT, exchange, SEBI, stamp duty, GST)
          </Label>
        </div>
      </fieldset>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t pt-4">
        <Button type="submit" disabled={run.isPending}>
          {run.isPending ? <Loader2 className="animate-spin" /> : <Play />}
          {run.isPending ? "Running backtest…" : "Run Backtest"}
        </Button>
        {run.isPending ? (
          <p className="text-sm text-muted-foreground" role="status">
            Simulating candle by candle. This can take several seconds: keep this tab open.
          </p>
        ) : null}
      </div>
    </form>
  );
}
