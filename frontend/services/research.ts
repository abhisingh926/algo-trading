import { api, request, requestBlob } from "@/lib/api";
import type {
  AgentTrace,
  CandidateList,
  CandidatesQuery,
  MarketOverview,
  OverallCalibration,
  PendingCalibrationRun,
  ReportSummary,
  ResearchReport,
  ResearchRunRead,
  ResearchSummaryRead,
  RunCalibration,
  RunRequest,
  ScoreHistory,
  SectorOverview,
  SourcesView,
  SourceRegistryRead,
  SourceRegistryUpdate,
  UniverseRead,
  WeightSetCreate,
  WeightSetRead,
} from "@/types/research";

/** Symbols can contain & and - (M&M, BAJAJ-AUTO), so they are always URL-encoded in paths. */
const sym = (symbol: string) => encodeURIComponent(symbol);

export const researchService = {
  startRun: (body: RunRequest) => api.post<ResearchRunRead>("/research/run", body),
  summary: () => api.get<ResearchSummaryRead>("/research/summary"),
  runs: (limit = 30, offset = 0) => api.get<ResearchRunRead[]>("/research/runs", { limit, offset }),
  run: (id: string) => api.get<ResearchRunRead>(`/research/runs/${encodeURIComponent(id)}`),
  candidates: (query: CandidatesQuery = {}) => api.get<CandidateList>("/research/candidates", query),
  market: (runId?: string) => api.get<MarketOverview>("/research/market", { run_id: runId }),
  sectors: (runId?: string) => api.get<SectorOverview>("/research/sectors", { run_id: runId }),
  report: (symbol: string, runId?: string) => api.get<ResearchReport>(`/research/${sym(symbol)}`, { run_id: runId }),
  symbolHistory: (symbol: string, limit = 30) =>
    api.get<ReportSummary[]>(`/research/${sym(symbol)}/history`, { limit }),
  scoreHistory: (symbol: string, limit = 30) =>
    api.get<ScoreHistory>(`/research/${sym(symbol)}/score-history`, { limit }),
  /** Same shape as /sources: claims, their status and the confidence breakdown. */
  verification: (symbol: string, runId?: string) =>
    api.get<SourcesView>(`/research/${sym(symbol)}/verification`, { run_id: runId }),
  /** One entry per agent, for auditing. */
  agentTrace: (symbol: string, runId?: string) =>
    api.get<AgentTrace[]>(`/research/${sym(symbol)}/agent-trace`, { run_id: runId }),
  /** These four always answer 501 for now. The ApiError carries the backend's own explanation. */
  news: (symbol: string) => request<unknown>(`/research/${sym(symbol)}/news`),
  fundamentals: (symbol: string) => request<unknown>(`/research/${sym(symbol)}/fundamentals`),
  corporateEvents: (symbol: string) => request<unknown>(`/research/${sym(symbol)}/corporate-events`),
  derivatives: (symbol: string) => request<unknown>(`/research/${sym(symbol)}/derivatives`),

  /** Calibration: what the market actually did after past scores. */
  calibration: () => api.get<OverallCalibration>("/research/calibration"),
  calibrationPending: () => api.get<PendingCalibrationRun[]>("/research/calibration/pending"),
  runCalibration: (runId: string) => api.get<RunCalibration>(`/research/runs/${encodeURIComponent(runId)}/calibration`),
  calibrateRun: (runId: string) => api.post<RunCalibration>(`/research/runs/${encodeURIComponent(runId)}/calibrate`),
  exportReport: (symbol: string, format: "json" | "csv", runId?: string) =>
    requestBlob(`/research/${sym(symbol)}/export`, { format, run_id: runId }),

  weights: () => api.get<WeightSetRead[]>("/research/weights"),
  proposeWeights: (body: WeightSetCreate) => api.post<WeightSetRead>("/research/weights", body),
  approveWeights: (id: string) => api.post<WeightSetRead>(`/research/weights/${encodeURIComponent(id)}/approve`),
  sourceRegistry: () => api.get<SourceRegistryRead[]>("/research/source-registry"),
  updateSource: (id: string, body: SourceRegistryUpdate) =>
    api.put<SourceRegistryRead>(`/research/source-registry/${encodeURIComponent(id)}`, body),
  universes: () => api.get<UniverseRead[]>("/research/universes"),
  universe: (name: string) => api.get<UniverseRead>(`/research/universes/${encodeURIComponent(name)}`),
};
