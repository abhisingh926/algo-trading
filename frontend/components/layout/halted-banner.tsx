"use client";

import { OctagonX } from "lucide-react";
import { ResumeTradingButton } from "@/components/layout/kill-switch";
import { useRiskConfig } from "@/hooks/use-risk";
import { useSystemStatus } from "@/hooks/use-system";
import { formatDateTime } from "@/lib/format";

export function HaltedBanner() {
  const { data } = useSystemStatus();
  const halted = data?.system_state === "HALTED" || data?.kill_switch_active === true;
  const risk = useRiskConfig();
  if (!halted) return null;

  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-red-700 bg-red-600 px-3 py-2.5 text-white sm:px-5"
    >
      <OctagonX className="size-5 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold tracking-wide uppercase">Trading halted: kill switch active</p>
        <p className="text-xs text-white/85">
          All strategies are stopped and new orders are blocked.
          {risk.data?.kill_switch_activated_at
            ? ` Activated ${formatDateTime(risk.data.kill_switch_activated_at)} IST.`
            : ""}
          {risk.data?.kill_switch_reason ? ` Reason: ${risk.data.kill_switch_reason}` : ""}
        </p>
      </div>
      <ResumeTradingButton className="border-white/40 bg-white text-red-700 hover:bg-white/90 hover:text-red-800 dark:border-white/40 dark:bg-white dark:hover:bg-white/90" />
    </div>
  );
}
