"use client";

import { useQuery } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS, POLL_SLOW_MS } from "@/lib/query-client";
import { dashboardService } from "@/services/dashboard";

export function useDashboardSummary() {
  return useQuery({
    queryKey: qk.dashboardSummary,
    queryFn: dashboardService.summary,
    refetchInterval: POLL_FAST_MS,
  });
}

export function useDashboardPnl(days = 30) {
  return useQuery({
    queryKey: qk.dashboardPnl(days),
    queryFn: () => dashboardService.pnl(days),
    refetchInterval: POLL_SLOW_MS,
    placeholderData: (prev) => prev,
  });
}

export function usePerformance() {
  return useQuery({
    queryKey: qk.dashboardPerformance,
    queryFn: dashboardService.performance,
    refetchInterval: POLL_SLOW_MS,
  });
}
