"use client";

import { useState } from "react";
import { OctagonX, Play } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useKillSwitch, useRiskConfig } from "@/hooks/use-risk";
import { cn } from "@/lib/utils";

export function KillSwitchButton({ className, disabled }: { className?: string; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const killSwitch = useKillSwitch();
  const risk = useRiskConfig();
  const closesPositions = risk.data?.close_positions_on_kill_switch;

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        disabled={disabled}
        className={cn(
          "bg-red-600 font-bold tracking-wide text-white uppercase hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700",
          className,
        )}
      >
        <OctagonX /> Kill switch
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Activate kill switch?"
        description="This immediately halts all automated and manual trading."
        confirmLabel="Halt all trading"
        destructive
        pending={killSwitch.isPending}
        onConfirm={() =>
          killSwitch.mutate(
            { activate: true, reason: reason.trim() },
            {
              onSuccess: () => {
                setOpen(false);
                setReason("");
              },
            },
          )
        }
      >
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          <li>Stops all running strategies</li>
          <li>Blocks all new orders until trading is resumed</li>
          <li>Cancels all pending orders</li>
          <li>
            {closesPositions === true ? (
              <span className="font-medium text-loss">
                Closes all open positions at market (enabled in risk settings)
              </span>
            ) : closesPositions === false ? (
              "Does NOT close open positions (can be enabled in risk settings)"
            ) : (
              "Does not close open positions unless configured in risk settings"
            )}
          </li>
        </ul>
        <div className="grid gap-1.5">
          <Label htmlFor="kill-reason">Reason (optional)</Label>
          <Textarea
            id="kill-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. unexpected market volatility"
            rows={2}
            maxLength={500}
          />
        </div>
      </ConfirmDialog>
    </>
  );
}

export function ResumeTradingButton({ className }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const killSwitch = useKillSwitch();
  return (
    <>
      <Button variant="outline" className={className} onClick={() => setOpen(true)}>
        <Play /> Resume trading
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Resume trading?"
        description="This deactivates the kill switch and allows new orders again. Strategies stay stopped: restart each one manually from the Strategies page."
        confirmLabel="Resume trading"
        pending={killSwitch.isPending}
        onConfirm={() =>
          killSwitch.mutate({ activate: false }, { onSuccess: () => setOpen(false) })
        }
      />
    </>
  );
}
