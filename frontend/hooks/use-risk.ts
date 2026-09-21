"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { riskService } from "@/services/risk";
import type { RiskConfigurationUpdate } from "@/types";

export function useRiskConfig() {
  return useQuery({ queryKey: qk.riskConfig, queryFn: riskService.get });
}

export function useRiskStatus() {
  return useQuery({
    queryKey: qk.riskStatus,
    queryFn: riskService.status,
    refetchInterval: POLL_FAST_MS,
  });
}

export function useUpdateRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RiskConfigurationUpdate) => riskService.update(body),
    onSuccess: () => {
      toastSuccess("Risk limits saved");
      void qc.invalidateQueries({ queryKey: qk.risk });
      void qc.invalidateQueries({ queryKey: qk.onboarding });
    },
    onError: toastError,
  });
}

export function useKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ activate, reason }: { activate: boolean; reason?: string }) =>
      riskService.killSwitch({ activate, confirm: true, reason: reason || undefined }),
    onSuccess: (r) => {
      const counts = `Strategies stopped: ${r.strategies_stopped} · Orders cancelled: ${r.orders_cancelled} · Positions closed: ${r.positions_closed}`;
      if (r.kill_switch_active) {
        toastSuccess("Kill switch activated: trading HALTED", `${r.message} — ${counts}`);
      } else {
        toastSuccess("Trading resumed", r.message);
      }
    },
    onError: toastError,
    // The kill switch touches everything: refresh the whole cache.
    onSettled: () => void qc.invalidateQueries(),
  });
}
