"use client";

import { useState } from "react";
import { AlertTriangle, Loader2, Plus } from "lucide-react";
import { Field, parseNumber, SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { ModeBadge } from "@/components/trading/badges";
import { InstrumentCombobox } from "@/components/trading/instrument-combobox";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useBrokerStatus } from "@/hooks/use-brokers";
import { useCreateOrder } from "@/hooks/use-orders";
import { useSystemStatus } from "@/hooks/use-system";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { OrderCreate, OrderSide, OrderType, ProductType } from "@/types";

const TYPE_OPTIONS: SelectOption<OrderType>[] = [
  { value: "MARKET", label: "Market" },
  { value: "LIMIT", label: "Limit" },
  { value: "SL", label: "Stop loss limit (SL)" },
  { value: "SL-M", label: "Stop loss market (SL-M)" },
];
const PRODUCT_OPTIONS: SelectOption<ProductType>[] = [
  { value: "INTRADAY", label: "Intraday" },
  { value: "DELIVERY", label: "Delivery" },
];

const needsPrice = (t: OrderType) => t === "LIMIT" || t === "SL";
const needsTrigger = (t: OrderType) => t === "SL" || t === "SL-M";

const EMPTY = {
  symbol: "",
  exchange: "NSE",
  side: "BUY" as OrderSide,
  order_type: "MARKET" as OrderType,
  product_type: "INTRADAY" as ProductType,
  quantity: "1",
  price: "",
  trigger_price: "",
  stop_loss: "",
  target: "",
};

export function NewOrderDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const system = useSystemStatus();
  const brokerStatus = useBrokerStatus();
  const create = useCreateOrder();
  const halted = system.data?.kill_switch_active === true;
  const mode = system.data?.trading_mode;

  const set = <K extends keyof typeof EMPTY>(key: K, value: (typeof EMPTY)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!form.symbol) errs.symbol = "Select a symbol";
    const quantity = parseNumber(form.quantity);
    if (quantity === null || !Number.isInteger(quantity) || quantity <= 0)
      errs.quantity = "Quantity must be a whole number above 0";

    const optional = (key: "price" | "trigger_price" | "stop_loss" | "target", required: boolean) => {
      const raw = form[key].trim();
      const n = parseNumber(raw);
      if (raw === "" && required) errs[key] = "Required for this order type";
      else if (raw !== "" && (n === null || n <= 0)) errs[key] = "Must be greater than 0";
      return n ?? undefined;
    };
    const price = needsPrice(form.order_type) ? optional("price", true) : undefined;
    const trigger = needsTrigger(form.order_type) ? optional("trigger_price", true) : undefined;
    const stopLoss = optional("stop_loss", false);
    const target = optional("target", false);

    setErrors(errs);
    if (Object.keys(errs).length > 0 || quantity === null) return;

    const body: OrderCreate = {
      symbol: form.symbol,
      exchange: form.exchange,
      side: form.side,
      order_type: form.order_type,
      product_type: form.product_type,
      quantity,
      price,
      trigger_price: trigger,
      stop_loss: stopLoss,
      target,
    };
    create.mutate(body, {
      onSuccess: () => {
        setOpen(false);
        setForm(EMPTY);
      },
      onError: (err) => {
        if (err instanceof ApiError) {
          setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field, x.message])));
        }
      },
    });
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <Plus /> New Order
      </Button>
      <Dialog open={open} onOpenChange={(o) => setOpen(o)}>
        <DialogContent className="sm:max-w-lg">
          <form onSubmit={onSubmit} noValidate className="grid gap-4">
            <DialogHeader>
              <DialogTitle>New manual order</DialogTitle>
              <DialogDescription>Manual orders pass through the same risk checks as strategy orders.</DialogDescription>
            </DialogHeader>

            <div
              className={cn(
                "flex flex-wrap items-center gap-2 rounded-md border p-2.5 text-sm",
                mode === "LIVE" ? "border-loss/40 bg-loss/10" : "bg-muted/40",
              )}
            >
              {mode ? (
                <>
                  <span>This order will be routed in</span> <ModeBadge mode={mode} /> <span>mode.</span>
                </>
              ) : (
                <span className="text-muted-foreground">Trading mode unknown: backend status unavailable.</span>
              )}
              {brokerStatus.data ? (
                <span className="basis-full text-xs text-muted-foreground">{brokerStatus.data.order_routing}</span>
              ) : null}
              {mode === "LIVE" ? (
                <span className="flex basis-full items-center gap-1.5 text-xs font-medium text-loss">
                  <AlertTriangle className="size-3.5" /> Real money: this order goes to the exchange.
                </span>
              ) : null}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Symbol" htmlFor="order-symbol" error={errors.symbol} className="sm:col-span-2">
                <InstrumentCombobox
                  id="order-symbol"
                  symbol={form.symbol}
                  exchange={form.exchange}
                  onSelect={(i) => setForm((f) => ({ ...f, symbol: i.symbol, exchange: i.exchange }))}
                  invalid={!!errors.symbol}
                />
              </Field>
              <Field label="Side">
                <div className="grid grid-cols-2 gap-1 rounded-lg border p-0.5" role="radiogroup" aria-label="Side">
                  {(["BUY", "SELL"] as const).map((s) => (
                    <button
                      key={s}
                      type="button"
                      role="radio"
                      aria-checked={form.side === s}
                      onClick={() => set("side", s)}
                      className={cn(
                        "h-7 rounded-md text-sm font-semibold transition-colors",
                        form.side === s
                          ? s === "BUY"
                            ? "bg-profit/20 text-profit"
                            : "bg-loss/20 text-loss"
                          : "text-muted-foreground hover:bg-muted",
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </Field>
              <Field label="Quantity" htmlFor="order-qty" error={errors.quantity}>
                <Input
                  id="order-qty"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  step={1}
                  value={form.quantity}
                  onChange={(e) => set("quantity", e.target.value)}
                  aria-invalid={!!errors.quantity}
                />
              </Field>
              <Field label="Order type" htmlFor="order-type">
                <SimpleSelect
                  id="order-type"
                  value={form.order_type}
                  onChange={(v) => set("order_type", v)}
                  options={TYPE_OPTIONS}
                />
              </Field>
              <Field label="Product" htmlFor="order-product">
                <SimpleSelect
                  id="order-product"
                  value={form.product_type}
                  onChange={(v) => set("product_type", v)}
                  options={PRODUCT_OPTIONS}
                />
              </Field>
              {needsPrice(form.order_type) ? (
                <PriceField id="order-price" label="Limit price (₹)" value={form.price} error={errors.price} onChange={(v) => set("price", v)} />
              ) : null}
              {needsTrigger(form.order_type) ? (
                <PriceField id="order-trigger" label="Trigger price (₹)" value={form.trigger_price} error={errors.trigger_price} onChange={(v) => set("trigger_price", v)} />
              ) : null}
              <PriceField id="order-sl" label="Stop loss (₹, optional)" value={form.stop_loss} error={errors.stop_loss} onChange={(v) => set("stop_loss", v)} />
              <PriceField id="order-target" label="Target (₹, optional)" value={form.target} error={errors.target} onChange={(v) => set("target", v)} />
            </div>

            {halted ? (
              <p className="text-sm font-medium text-loss">Kill switch is active: new orders are blocked.</p>
            ) : null}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={create.isPending}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={create.isPending || halted}
                className={cn(
                  "text-white",
                  form.side === "BUY" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700",
                )}
              >
                {create.isPending ? <Loader2 className="animate-spin" /> : null}
                {form.side} {form.symbol || "order"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

function PriceField({
  id,
  label,
  value,
  error,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
}) {
  return (
    <Field label={label} htmlFor={id} error={error}>
      <Input
        id={id}
        type="number"
        inputMode="decimal"
        min={0}
        step="0.05"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={!!error}
      />
    </Field>
  );
}
