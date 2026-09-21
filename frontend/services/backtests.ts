import { api } from "@/lib/api";
import type {
  Backtest,
  BacktestCreate,
  BacktestEquityPoint,
  BacktestReport,
  BacktestTrade,
} from "@/types";

export const backtestsService = {
  run: (body: BacktestCreate) => api.post<Backtest>("/backtests", body),
  list: (limit = 50) => api.get<Backtest[]>("/backtests", { limit }),
  get: (id: string) => api.get<Backtest>(`/backtests/${id}`),
  trades: (id: string) => api.get<BacktestTrade[]>(`/backtests/${id}/trades`),
  equityCurve: (id: string) => api.get<BacktestEquityPoint[]>(`/backtests/${id}/equity-curve`),
  report: (id: string) => api.get<BacktestReport>(`/backtests/${id}/report`),
  remove: (id: string) => api.delete<null>(`/backtests/${id}`),
};
