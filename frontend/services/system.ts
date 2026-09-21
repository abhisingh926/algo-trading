import { api, request } from "@/lib/api";
import type { EventsQuery, Health, SystemConfig, SystemEvent, SystemStatus } from "@/types";

export const systemService = {
  health: () => request<Health>("/health", { prefixed: false }),
  status: () => api.get<SystemStatus>("/system/status"),
  config: () => api.get<SystemConfig>("/system/config"),
  events: (query: EventsQuery = {}) => api.get<SystemEvent[]>("/events", query),
};
