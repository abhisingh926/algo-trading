"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Field, parseNumber } from "@/components/layout/form-controls";
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
import { useUpdatePosition } from "@/hooks/use-positions";
import { formatPrice } from "@/lib/format";
import type { Position } from "@/types";

export function EditPositionDialog({
  position,
  onOpenChange,
}: {
  position: Position | null;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={!!position} onOpenChange={(o) => onOpenChange(o)}>
      <DialogContent>
        {position ? (
          <EditForm key={position.id} position={position} onDone={() => onOpenChange(false)} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function EditForm({ position, onDone }: { position: Position; onDone: () => void }) {
  const update = useUpdatePosition();
  const [stopLoss, setStopLoss] = useState(position.stop_loss === null ? "" : String(position.stop_loss));
  const [target, setTarget] = useState(position.target === null ? "" : String(position.target));
  const [errors, setErrors] = useState<Record<string, string>>({});

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    const sl = parseNumber(stopLoss);
    const tg = parseNumber(target);
    if (stopLoss.trim() !== "" && (sl === null || sl <= 0)) errs.stop_loss = "Must be greater than 0";
    if (target.trim() !== "" && (tg === null || tg <= 0)) errs.target = "Must be greater than 0";
    const entry = position.average_entry_price;
    const long = position.side === "LONG";
    if (!errs.stop_loss && sl !== null && (long ? sl >= entry : sl <= entry))
      errs.stop_loss = `For a ${position.side} position the stop loss must be ${long ? "below" : "above"} entry`;
    if (!errs.target && tg !== null && (long ? tg <= entry : tg >= entry))
      errs.target = `For a ${position.side} position the target must be ${long ? "above" : "below"} entry`;
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    // null clears the level on the backend.
    update.mutate({ id: position.id, body: { stop_loss: sl, target: tg } }, { onSuccess: onDone });
  };

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-4">
      <DialogHeader>
        <DialogTitle>
          Edit SL / target: {position.symbol}
        </DialogTitle>
        <DialogDescription>
          {position.side} {position.quantity} @ {formatPrice(position.average_entry_price)} · LTP{" "}
          {formatPrice(position.last_price)}. Leave a field blank to remove that level.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Stop loss (₹)" htmlFor="pos-sl" error={errors.stop_loss}>
          <Input
            id="pos-sl"
            type="number"
            inputMode="decimal"
            min={0}
            step="0.05"
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            aria-invalid={!!errors.stop_loss}
          />
        </Field>
        <Field label="Target (₹)" htmlFor="pos-target" error={errors.target}>
          <Input
            id="pos-target"
            type="number"
            inputMode="decimal"
            min={0}
            step="0.05"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            aria-invalid={!!errors.target}
          />
        </Field>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone} disabled={update.isPending}>
          Cancel
        </Button>
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? <Loader2 className="animate-spin" /> : null} Save
        </Button>
      </DialogFooter>
    </form>
  );
}
