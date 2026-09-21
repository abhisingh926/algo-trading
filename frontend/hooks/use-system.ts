"use client";

import { useQuery } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS } from "@/lib/query-client";
import { systemService } from "@/services/system";
import type { EventsQuery } from "@/types";

export function useSystemStatus() {
  return useQuery({
    queryKey: qk.systemStatus,
    queryFn: systemService.status,
    refetchInterval: POLL_FAST_MS,
  });
}

export function useSystemConfig() {
  return useQuery({ queryKey: qk.systemConfig, queryFn: systemService.config, staleTime: 60_000 });
}

export function useEvents(query: EventsQuery, autoRefresh: boolean) {
  return useQuery({
    queryKey: qk.events(query),
    queryFn: () => systemService.events(query),
    refetchInterval: autoRefresh ? POLL_FAST_MS : false,
    placeholderData: (prev) => prev,
  });
}
