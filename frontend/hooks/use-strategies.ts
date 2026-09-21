"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { strategiesService } from "@/services/strategies";
import type { StrategyCreate, StrategyUpdate } from "@/types";

export function useStrategyTypes() {
  return useQuery({
    queryKey: qk.strategyTypes,
    queryFn: strategiesService.types,
    staleTime: 5 * 60_000,
  });
}

export function useStrategies(poll = true) {
  return useQuery({
    queryKey: qk.strategiesList,
    queryFn: strategiesService.list,
    refetchInterval: poll ? POLL_FAST_MS : false,
  });
}

export function useStrategy(id: string | null) {
  return useQuery({
    queryKey: qk.strategy(id ?? ""),
    queryFn: () => strategiesService.get(id as string),
    enabled: !!id,
  });
}

export function useStrategySignals(id: string | null, limit = 50) {
  return useQuery({
    queryKey: qk.strategySignals(id ?? "", limit),
    queryFn: () => strategiesService.signals(id as string, limit),
    enabled: !!id,
    refetchInterval: POLL_FAST_MS,
  });
}

function useInvalidateStrategies() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: qk.strategies });
    void qc.invalidateQueries({ queryKey: qk.dashboard });
    void qc.invalidateQueries({ queryKey: qk.systemStatus });
    void qc.invalidateQueries({ queryKey: qk.eventsAll });
    void qc.invalidateQueries({ queryKey: qk.onboarding });
  };
}

/** Save mutations do not toast success themselves: the builder chains follow-up actions. */
export function useCreateStrategy() {
  const invalidate = useInvalidateStrategies();
  return useMutation({
    mutationFn: (body: StrategyCreate) => strategiesService.create(body),
    onSuccess: invalidate,
    onError: toastError,
  });
}

export function useUpdateStrategy() {
  const invalidate = useInvalidateStrategies();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: StrategyUpdate }) =>
      strategiesService.update(id, body),
    onSuccess: invalidate,
    onError: toastError,
  });
}

export function useDeleteStrategy() {
  const invalidate = useInvalidateStrategies();
  return useMutation({
    mutationFn: (id: string) => strategiesService.remove(id),
    onSuccess: () => {
      toastSuccess("Strategy deleted");
      invalidate();
    },
    onError: toastError,
  });
}

export function useStartStrategy() {
  const invalidate = useInvalidateStrategies();
  return useMutation({
    mutationFn: (id: string) => strategiesService.start(id),
    onSuccess: (s) => {
      toastSuccess("Strategy started", `${s.name} is running in ${s.trading_mode} mode`);
      invalidate();
    },
    onError: toastError,
  });
}

export function useStopStrategy() {
  const invalidate = useInvalidateStrategies();
  return useMutation({
    mutationFn: (id: string) => strategiesService.stop(id),
    onSuccess: (s) => {
      toastSuccess("Strategy stopped", s.name);
      invalidate();
    },
    onError: toastError,
  });
}
