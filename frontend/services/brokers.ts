import { api } from "@/lib/api";
import type {
  BrokerAccount,
  BrokerAccountCreate,
  BrokerAccountUpdate,
  BrokerStatus,
  BrokerTestResult,
} from "@/types";

export const brokersService = {
  list: () => api.get<BrokerAccount[]>("/brokers"),
  create: (body: BrokerAccountCreate) => api.post<BrokerAccount>("/brokers", body),
  update: (id: string, body: BrokerAccountUpdate) => api.put<BrokerAccount>(`/brokers/${id}`, body),
  remove: (id: string) => api.delete<null>(`/brokers/${id}`),
  status: () => api.get<BrokerStatus>("/brokers/status"),
  test: (brokerAccountId: string) =>
    api.post<BrokerTestResult>("/brokers/test", { broker_account_id: brokerAccountId }),
};
