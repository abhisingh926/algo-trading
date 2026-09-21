import { api } from "@/lib/api";
import type { Signal, Strategy, StrategyCreate, StrategyTypeInfo, StrategyUpdate } from "@/types";

export const strategiesService = {
  types: () => api.get<StrategyTypeInfo[]>("/strategies/types"),
  list: () => api.get<Strategy[]>("/strategies"),
  get: (id: string) => api.get<Strategy>(`/strategies/${id}`),
  create: (body: StrategyCreate) => api.post<Strategy>("/strategies", body),
  update: (id: string, body: StrategyUpdate) => api.put<Strategy>(`/strategies/${id}`, body),
  remove: (id: string) => api.delete<null>(`/strategies/${id}`),
  start: (id: string) => api.post<Strategy>(`/strategies/${id}/start`),
  stop: (id: string) => api.post<Strategy>(`/strategies/${id}/stop`),
  signals: (id: string, limit = 50) => api.get<Signal[]>(`/strategies/${id}/signals`, { limit }),
  allSignals: (limit = 50) => api.get<Signal[]>("/signals", { limit }),
};
