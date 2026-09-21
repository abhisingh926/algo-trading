"use client";

import { useState } from "react";
import { Loader2, Save } from "lucide-react";
import { Field, parseNumber } from "@/components/layout/form-controls";
import { ErrorState } from "@/components/tables/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useRiskConfig, useUpdateRisk } from "@/hooks/use-risk";
import { ApiError } from "@/lib/api";
import { formatDateTime, fractionToPercent, percentToFraction } from "@/lib/format";
import type { RiskConfiguration, RiskConfigurationUpdate } from "@/types";

type NumericKey = Exclude<keyof RiskConfigurationUpdate, "close_positions_on_kill_switch">;

interface FieldDef {
  key: NumericKey;
  label: string;
  hint: string;
  kind: "percent" | "inr" | "count";
}

const FIELDS: FieldDef[] = [
  { key: "max_risk_per_trade", label: "Max risk per trade (%)", hint: "Largest share of capital one trade may risk", kind: "percent" },
  { key: "max_daily_loss", label: "Max daily loss (₹)", hint: "Trading is blocked for the day once this loss is hit", kind: "inr" },
  { key: "max_trades_per_day", label: "Max trades per day", hint: "Across all strategies and manual orders", kind: "count" },
  { key: "max_open_positions", label: "Max open positions", hint: "Simultaneous open positions", kind: "count" },
  { key: "max_position_size", label: "Max position size (qty)", hint: "Largest quantity for a single position", kind: "count" },
  { key: "max_order_value", label: "Max order value (₹)", hint: "Largest notional value of a single order", kind: "inr" },
  { key: "max_consecutive_losses", label: "Max consecutive losses", hint: "Losing streak that blocks further trading", kind: "count" },
  { key: "max_strategy_drawdown", label: "Max strategy drawdown (%)", hint: "A strategy is stopped beyond this drawdown", kind: "percent" },
];

export function RiskLimitsForm() {
  const { data, isLoading, error, refetch } = useRiskConfig();
  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  return data ? <LimitsForm key={data.id} config={data} /> : null;
}

function toInput(config: RiskConfiguration, f: FieldDef): string {
  const v = config[f.key];
  return String(f.kind === "percent" ? fractionToPercent(v) : v);
}

function LimitsForm({ config }: { config: RiskConfiguration }) {
  const update = useUpdateRisk();
  const [values, setValues] = useState<Record<NumericKey, string>>(
    () => Object.fromEntries(FIELDS.map((f) => [f.key, toInput(config, f)])) as Record<NumericKey, string>,
  );
  const [closeOnKill, setCloseOnKill] = useState(config.close_positions_on_kill_switch);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const dirty =
    closeOnKill !== config.close_positions_on_kill_switch ||
    FIELDS.some((f) => values[f.key] !== toInput(config, f));

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    const body: RiskConfigurationUpdate = { close_positions_on_kill_switch: closeOnKill };
    for (const f of FIELDS) {
      const n = parseNumber(values[f.key]);
      if (n === null || n <= 0) errs[f.key] = "Must be greater than 0";
      else if (f.kind === "percent" && n > 100) errs[f.key] = "Cannot exceed 100%";
      else if (f.kind === "count" && !Number.isInteger(n)) errs[f.key] = "Must be a whole number";
      else body[f.key] = f.kind === "percent" ? percentToFraction(n) : n;
    }
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    update.mutate(body, {
      onError: (err) => {
        if (err instanceof ApiError)
          setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field, x.message])));
      },
    });
  };

  return (
    <form onSubmit={onSubmit} noValidate className="rounded-lg border bg-card p-4">
      <fieldset disabled={update.isPending} className="grid gap-4 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <Field key={f.key} label={f.label} htmlFor={`risk-${f.key}`} hint={f.hint} error={errors[f.key]}>
            <Input
              id={`risk-${f.key}`}
              type="number"
              inputMode={f.kind === "count" ? "numeric" : "decimal"}
              min={0}
              max={f.kind === "percent" ? 100 : undefined}
              step={f.kind === "count" ? 1 : "any"}
              value={values[f.key]}
              onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              aria-invalid={!!errors[f.key]}
            />
          </Field>
        ))}
        <div className="flex items-start gap-2.5 rounded-md border p-3 sm:col-span-2">
          <Switch
            id="risk-close-on-kill"
            className="mt-0.5"
            checked={closeOnKill}
            onCheckedChange={(c) => setCloseOnKill(c)}
          />
          <div>
            <Label htmlFor="risk-close-on-kill">Close all positions when the kill switch is activated</Label>
            <p className="mt-1 text-xs text-muted-foreground">
              When off, the kill switch stops strategies and cancels pending orders but leaves open positions for you
              to manage manually.
            </p>
          </div>
        </div>
      </fieldset>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t pt-4">
        <Button type="submit" disabled={update.isPending || !dirty}>
          {update.isPending ? <Loader2 className="animate-spin" /> : <Save />} Save limits
        </Button>
        <p className="text-xs text-muted-foreground">Last updated {formatDateTime(config.updated_at)} IST</p>
      </div>
    </form>
  );
}
