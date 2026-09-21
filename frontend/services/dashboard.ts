import { api } from "@/lib/api";
import type { DashboardPnl, DashboardSummary, Performance } from "@/types";

export const dashboardService = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
  pnl: (days = 30) => api.get<DashboardPnl>("/dashboard/pnl", { days }),
  performance: () => api.get<Performance>("/dashboard/performance"),
};
