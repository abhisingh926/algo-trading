"use client";

import { useQuery } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_SLOW_MS } from "@/lib/query-client";
import { tradesService } from "@/services/trades";
import type { TradesQuery } from "@/types";

export function useTrades(query: TradesQuery = {}) {
  return useQuery({
    queryKey: qk.tradesList(query),
    queryFn: () => tradesService.list(query),
    refetchInterval: POLL_SLOW_MS,
    placeholderData: (prev) => prev,
  });
}
