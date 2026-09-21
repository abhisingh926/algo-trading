"use client";

import { useQuery } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { marketDataService } from "@/services/market-data";

export function useInstruments(search: string, enabled = true) {
  return useQuery({
    queryKey: qk.instruments(search),
    queryFn: ({ signal }) => marketDataService.instruments(search, 50, signal),
    enabled,
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  });
}
