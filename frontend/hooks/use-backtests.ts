"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { toastError, toastSuccess } from "@/lib/toast";
import { backtestsService } from "@/services/backtests";
import type { BacktestCreate } from "@/types";

export function useBacktests(limit = 50) {
  return useQuery({
    queryKey: qk.backtestsList(limit),
    queryFn: () => backtestsService.list(limit),
  });
}

export function useBacktestReport(id: string | null) {
  return useQuery({
    queryKey: qk.backtestReport(id ?? ""),
    queryFn: () => backtestsService.report(id as string),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BacktestCreate) => backtestsService.run(body),
    onSuccess: (b) => {
      if (b.status === "FAILED") {
        toastError(new Error(`Backtest failed: ${b.error_message ?? "unknown error"}`));
      } else {
        toastSuccess("Backtest completed", b.name);
      }
    },
    onError: toastError,
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.backtests });
      void qc.invalidateQueries({ queryKey: qk.eventsAll });
    },
  });
}

export function useDeleteBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => backtestsService.remove(id),
    onSuccess: (_d, id) => {
      toastSuccess("Backtest deleted");
      qc.removeQueries({ queryKey: qk.backtestReport(id) });
      void qc.invalidateQueries({ queryKey: qk.backtests });
    },
    onError: toastError,
  });
}
