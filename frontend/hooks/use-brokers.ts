"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_SLOW_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { brokersService } from "@/services/brokers";
import type { BrokerAccountCreate, BrokerAccountUpdate } from "@/types";

export function useBrokers() {
  return useQuery({ queryKey: qk.brokersList, queryFn: brokersService.list });
}

export function useBrokerStatus() {
  return useQuery({
    queryKey: qk.brokerStatus,
    queryFn: brokersService.status,
    refetchInterval: POLL_SLOW_MS,
  });
}

function useInvalidateBrokers() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: qk.brokers });
    void qc.invalidateQueries({ queryKey: qk.systemStatus });
  };
}

export function useCreateBroker() {
  const invalidate = useInvalidateBrokers();
  return useMutation({
    mutationFn: (body: BrokerAccountCreate) => brokersService.create(body),
    onSuccess: (b) => {
      toastSuccess("Broker account added", b.name);
      invalidate();
    },
    onError: toastError,
  });
}

export function useUpdateBroker() {
  const invalidate = useInvalidateBrokers();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: BrokerAccountUpdate }) =>
      brokersService.update(id, body),
    onSuccess: (b) => {
      toastSuccess("Broker account updated", b.name);
      invalidate();
    },
    onError: toastError,
  });
}

export function useDeleteBroker() {
  const invalidate = useInvalidateBrokers();
  return useMutation({
    mutationFn: (id: string) => brokersService.remove(id),
    onSuccess: () => {
      toastSuccess("Broker account deleted");
      invalidate();
    },
    onError: toastError,
  });
}

export function useTestBroker() {
  const invalidate = useInvalidateBrokers();
  return useMutation({
    mutationFn: (id: string) => brokersService.test(id),
    onSuccess: (r) => {
      const latency = r.latency_ms !== null ? ` (${Math.round(r.latency_ms)} ms)` : "";
      if (r.connected) toastSuccess(`${r.broker_type} connected${latency}`, r.detail);
      else toastError(new Error(`${r.broker_type} not connected: ${r.detail}`));
    },
    onError: toastError,
    onSettled: invalidate,
  });
}
