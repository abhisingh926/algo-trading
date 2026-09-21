import { api } from "@/lib/api";
import type {
  KillSwitchRequest,
  KillSwitchResult,
  RiskConfiguration,
  RiskConfigurationUpdate,
  RiskStatus,
} from "@/types";

export const riskService = {
  get: () => api.get<RiskConfiguration>("/risk"),
  update: (body: RiskConfigurationUpdate) => api.put<RiskConfiguration>("/risk", body),
  status: () => api.get<RiskStatus>("/risk/status"),
  killSwitch: (body: KillSwitchRequest) => api.post<KillSwitchResult>("/risk/kill-switch", body),
};
