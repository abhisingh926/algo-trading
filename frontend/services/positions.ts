import { api } from "@/lib/api";
import type { Order, Position, PositionStatusFilter, PositionUpdate } from "@/types";

export const positionsService = {
  list: (status: PositionStatusFilter = "open") => api.get<Position[]>("/positions", { status }),
  bySymbol: (symbol: string) => api.get<Position[]>(`/positions/${encodeURIComponent(symbol)}`),
  update: (id: string, body: PositionUpdate) => api.put<Position>(`/positions/${id}`, body),
  close: (id: string) => api.post<Order>(`/positions/${id}/close`),
};
