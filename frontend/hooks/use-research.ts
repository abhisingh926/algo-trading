"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { ApiError } from "@/lib/api";
import { POLL_FAST_MS, POLL_SLOW_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { marketDataService } from "@/services/market-data";
import { researchService } from "@/services/research";
import type { CandlesQuery } from "@/types";
import type {
  CandidatesQuery,
  ResearchRunRead,
  RunRequest,
  SourceRegistryUpdate,
  WeightSetCreate,
} from "@/types/research";

/** A run is still working while it is PENDING or RUNNING. */
export const isRunActive = (run: Pick<ResearchRunRead, "status"> | null | undefined): boolean =>
  !!run && (run.status === "PENDING" || run.status === "RUNNING");

/** Do not spam the toast area with 404s: "no run yet" is a normal state for the research pages. */
const noRunYet = (error: unknown) => error instanceof ApiError && (error.code === 404 || error.code === 409);

export function useResearchSummary() {
  return useQuery({
    queryKey: qk.researchSummary,
    queryFn: researchService.summary,
    refetchInterval: POLL_FAST_MS * 2,
  });
}

export function useResearchRuns(limit = 30) {
  return useQuery({
    queryKey: qk.researchRuns(limit),
    queryFn: () => researchService.runs(limit),
  });
}

/** Live progress of one run: polls every 2 seconds until it is COMPLETED or FAILED. */
export function useResearchRun(id: string | null) {
  return useQuery({
    queryKey: qk.researchRun(id ?? ""),
    queryFn: () => researchService.run(id as string),
    enabled: !!id,
    refetchInterval: (query) => (isRunActive(query.state.data) ? 2_000 : false),
    staleTime: 0,
  });
}

export function useCandidates(query: CandidatesQuery, enabled = true) {
  return useQuery({
    queryKey: qk.researchCandidates(query),
    queryFn: () => researchService.candidates(query),
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: POLL_SLOW_MS * 2,
    retry: (count, error) => !noRunYet(error) && count < 1,
  });
}

export function useResearchMarket(runId: string | null = null) {
  return useQuery({
    queryKey: qk.researchMarket(runId),
    queryFn: () => researchService.market(runId ?? undefined),
    retry: (count, error) => !noRunYet(error) && count < 1,
  });
}

export function useResearchSectors(runId: string | null = null) {
  return useQuery({
    queryKey: qk.researchSectors(runId),
    queryFn: () => researchService.sectors(runId ?? undefined),
    retry: (count, error) => !noRunYet(error) && count < 1,
  });
}

export function useResearchReport(symbol: string | null, runId: string | null = null) {
  return useQuery({
    queryKey: qk.researchReport(symbol ?? "", runId),
    queryFn: () => researchService.report(symbol as string, runId ?? undefined),
    enabled: !!symbol,
    staleTime: 30_000,
    retry: (count, error) => !noRunYet(error) && count < 1,
  });
}

export function useScoreHistory(symbol: string | null) {
  return useQuery({
    queryKey: qk.researchScoreHistory(symbol ?? ""),
    queryFn: () => researchService.scoreHistory(symbol as string),
    enabled: !!symbol,
    staleTime: 30_000,
    retry: (count, error) => !noRunYet(error) && count < 1,
  });
}

/** The news endpoint always answers 501 today; the query exists to show the backend's own explanation. */
export function useResearchNews(symbol: string | null) {
  return useQuery({
    queryKey: qk.researchNews(symbol ?? ""),
    queryFn: () => researchService.news(symbol as string),
    enabled: !!symbol,
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useStartResearchRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RunRequest) => researchService.startRun(body),
    onSuccess: (run) => {
      toastSuccess(`Research run #${run.run_number} started`, "You can follow each agent's progress below.");
      void qc.invalidateQueries({ queryKey: qk.researchSummary });
      void qc.invalidateQueries({ queryKey: qk.researchRuns(30) });
    },
    onError: (err) => {
      toastError(err);
      // 409: a run is already active. Refresh the summary so the page can follow that run.
      void qc.invalidateQueries({ queryKey: qk.researchSummary });
    },
  });
}

/** Called once when a tracked run reaches a terminal state, so every research view shows the new data. */
export function useRefreshResearchData() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: qk.research });
    void qc.invalidateQueries({ queryKey: qk.eventsAll });
  };
}

export function useWeights() {
  return useQuery({ queryKey: qk.researchWeights, queryFn: researchService.weights });
}

export function useProposeWeights() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WeightSetCreate) => researchService.proposeWeights(body),
    onSuccess: (w) => {
      toastSuccess("Weight set proposed", `${w.name} v${w.version} changes nothing until an administrator approves it.`);
      void qc.invalidateQueries({ queryKey: qk.researchWeights });
    },
    onError: toastError,
  });
}

export function useApproveWeights() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => researchService.approveWeights(id),
    onSuccess: (w) => {
      toastSuccess("Weight set approved", `${w.name} v${w.version} is now the active scoring model.`);
      void qc.invalidateQueries({ queryKey: qk.researchWeights });
    },
    onError: toastError,
  });
}

export function useSourceRegistry() {
  return useQuery({ queryKey: qk.researchSourceRegistry, queryFn: researchService.sourceRegistry });
}

export function useUpdateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SourceRegistryUpdate }) => researchService.updateSource(id, body),
    onSuccess: (s) => {
      toastSuccess("Source updated", `${s.name}: ${s.enabled ? "enabled" : "disabled"}`);
      void qc.invalidateQueries({ queryKey: qk.researchSourceRegistry });
    },
    onError: toastError,
  });
}

export function useUniverses() {
  return useQuery({ queryKey: qk.researchUniverses, queryFn: researchService.universes, staleTime: 60_000 });
}

export function useUniverse(name: string | null) {
  return useQuery({
    queryKey: qk.researchUniverse(name ?? ""),
    queryFn: () => researchService.universe(name as string),
    enabled: !!name,
    staleTime: 60_000,
  });
}

/** Candles for the report's price chart, from the existing market-data endpoint. */
export function useCandles(query: CandlesQuery | null) {
  return useQuery({
    queryKey: qk.candles(query ?? {}),
    queryFn: () => marketDataService.candles(query as CandlesQuery),
    enabled: !!query,
    staleTime: 60_000,
    retry: false,
  });
}
