import { api, request, requestBlob } from "@/lib/api";
import type {
  CandidateList,
  CandidatesQuery,
  MarketOverview,
  ReportSummary,
  ResearchReport,
  ResearchRunRead,
  ResearchSummaryRead,
  RunRequest,
  ScoreHistory,
  SectorOverview,
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
  report: (symbol: string, runId?: string) =>
    api.get<ResearchReport>(`/research/${sym(symbol)}`, { run_id: runId }),
  symbolHistory: (symbol: string, limit = 30) =>
    api.get<ReportSummary[]>(`/research/${sym(symbol)}/history`, { limit }),
  scoreHistory: (symbol: string, limit = 30) =>
    api.get<ScoreHistory>(`/research/${sym(symbol)}/score-history`, { limit }),
  /** Always answers 501 for now: no news source is connected. The ApiError carries the explanation. */
  news: (symbol: string) => request<unknown>(`/research/${sym(symbol)}/news`),
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
