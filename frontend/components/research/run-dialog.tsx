"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import { Field, SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
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
import { Textarea } from "@/components/ui/textarea";
import { useStartResearchRun, useUniverses } from "@/hooks/use-research";
import { ApiError } from "@/lib/api";
import { DEPTH_INFO } from "@/lib/research";
import { cn } from "@/lib/utils";
import type { ResearchDepth, ResearchRunRead, RunRequest } from "@/types/research";

const CUSTOM = "CUSTOM";
const SYMBOL_RE = /^[A-Z0-9&-]{1,20}$/;

/** Splits on commas, spaces and new lines; upper-cases; removes duplicates. Symbols may contain & and -. */
export function parseSymbols(raw: string): string[] {
  return [
    ...new Set(
      raw
        .split(/[\s,;]+/)
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean),
    ),
  ];
}

/** A datetime-local value is read as IST (UTC+05:30) and sent as an ISO instant. */
function istLocalToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(`${value}:00+05:30`);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

interface RunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStarted: (run: ResearchRunRead) => void;
  disabledReason?: string | null;
}

export function RunDialog({ open, onOpenChange, onStarted, disabledReason }: RunDialogProps) {
  const universes = useUniverses();
  const start = useStartResearchRun();
  const [universe, setUniverse] = useState("NIFTY50");
  const [symbolsText, setSymbolsText] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("STANDARD");
  const [timeMode, setTimeMode] = useState<"now" | "custom">("now");
  const [asOf, setAsOf] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const universeOptions: SelectOption[] = [
    ...(universes.data ?? []).map((u) => ({ value: u.name, label: `${u.name} (${u.count} stocks)` })),
    ...(universes.data?.some((u) => u.name === "NIFTY50") ? [] : [{ value: "NIFTY50", label: "NIFTY50" }]),
    { value: CUSTOM, label: "Custom list of symbols" },
  ];
  const symbols = parseSymbols(symbolsText);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (universe === CUSTOM) {
      if (symbols.length === 0) errs.symbols = "Enter at least one symbol";
      else {
        const bad = symbols.filter((s) => !SYMBOL_RE.test(s));
        if (bad.length > 0) errs.symbols = `Not valid symbols: ${bad.slice(0, 5).join(", ")}`;
      }
    }
    let iso: string | null = null;
    if (timeMode === "custom") {
      iso = istLocalToIso(asOf);
      if (!iso) errs.as_of = "Pick a date and time";
      else if (new Date(iso).getTime() > Date.now() + 60_000) errs.as_of = "The time cannot be in the future";
    }
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    const body: RunRequest = {
      market: "NSE",
      universe,
      research_type: "INTRADAY",
      depth,
      ...(universe === CUSTOM ? { symbols } : {}),
      ...(iso ? { as_of: iso } : {}),
    };
    start.mutate(body, {
      onSuccess: (run) => {
        onOpenChange(false);
        onStarted(run);
      },
      onError: (err) => {
        if (err instanceof ApiError) {
          setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field.replace(/^body\./, ""), x.message])));
        }
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => onOpenChange(o)}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-xl">
        <form onSubmit={submit} noValidate className="grid gap-4">
          <DialogHeader>
            <DialogTitle>New Research Scan</DialogTitle>
            <DialogDescription>
              Scans the chosen stocks, runs the research agents and ranks the results by Research Score. This is
              research only: nothing here places an order.
            </DialogDescription>
          </DialogHeader>

          <Field label="Universe" htmlFor="scan-universe" error={errors.universe}>
            <SimpleSelect id="scan-universe" value={universe} onChange={setUniverse} options={universeOptions} />
          </Field>

          {universe === CUSTOM ? (
            <Field
              label="Symbols"
              htmlFor="scan-symbols"
              error={errors.symbols}
              hint={`Separate with commas, spaces or new lines. Symbols such as M&M and BAJAJ-AUTO are fine. ${symbols.length} entered.`}
            >
              <Textarea
                id="scan-symbols"
                rows={3}
                value={symbolsText}
                onChange={(e) => setSymbolsText(e.target.value)}
                placeholder="RELIANCE, TCS, M&M, BAJAJ-AUTO"
                aria-invalid={!!errors.symbols}
              />
            </Field>
          ) : null}

          <fieldset className="grid gap-1.5">
            <legend className="mb-1.5 text-sm font-medium">Depth</legend>
            <div role="radiogroup" aria-label="Depth" className="grid gap-2">
              {(Object.keys(DEPTH_INFO) as ResearchDepth[]).map((d) => (
                <button
                  key={d}
                  type="button"
                  role="radio"
                  aria-checked={depth === d}
                  onClick={() => setDepth(d)}
                  className={cn(
                    "rounded-lg border p-2.5 text-left transition-colors hover:bg-muted/50",
                    depth === d && "border-primary bg-muted/60",
                  )}
                >
                  <span className="text-sm font-medium">{DEPTH_INFO[d].label}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">{DEPTH_INFO[d].text}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Research type" htmlFor="scan-type">
              <SimpleSelect
                id="scan-type"
                value="INTRADAY"
                onChange={() => {}}
                options={[{ value: "INTRADAY", label: "Intraday" }]}
              />
            </Field>
            <Field label="Time" htmlFor="scan-time-mode">
              <SimpleSelect
                id="scan-time-mode"
                value={timeMode}
                onChange={(v) => setTimeMode(v)}
                options={[
                  { value: "now", label: "Current" },
                  { value: "custom", label: "Custom date and time" },
                ]}
              />
            </Field>
          </div>
          {timeMode === "custom" ? (
            <Field
              label="Analyse the market as of (IST)"
              htmlFor="scan-as-of"
              error={errors.as_of}
              hint="Indian Standard Time. Useful for reviewing a past session."
            >
              <Input
                id="scan-as-of"
                type="datetime-local"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                aria-invalid={!!errors.as_of}
              />
            </Field>
          ) : null}

          {disabledReason ? <p className="text-sm text-warning">{disabledReason}</p> : null}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={start.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={start.isPending || !!disabledReason}>
              {start.isPending ? <Loader2 className="animate-spin" /> : <Play />} Start scan
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
