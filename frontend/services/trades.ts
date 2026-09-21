import { api } from "@/lib/api";
import type { Trade, TradesQuery } from "@/types";

export const tradesService = {
  list: (query: TradesQuery = {}) => api.get<Trade[]>("/trades", query),
  get: (id: string) => api.get<Trade>(`/trades/${id}`),
};
