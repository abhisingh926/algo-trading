"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { ordersService } from "@/services/orders";
import type { OrderCreate, OrdersQuery } from "@/types";

export function useOrders(query: OrdersQuery = {}) {
  return useQuery({
    queryKey: qk.ordersList(query),
    queryFn: () => ordersService.list(query),
    refetchInterval: POLL_FAST_MS,
    placeholderData: (prev) => prev,
  });
}

export function useOrder(id: string | null) {
  return useQuery({
    queryKey: qk.order(id ?? ""),
    queryFn: () => ordersService.get(id as string),
    enabled: !!id,
    refetchInterval: POLL_FAST_MS,
  });
}

function useInvalidateOrders() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: qk.orders });
    void qc.invalidateQueries({ queryKey: qk.positions });
    void qc.invalidateQueries({ queryKey: qk.trades });
    void qc.invalidateQueries({ queryKey: qk.dashboard });
    void qc.invalidateQueries({ queryKey: qk.risk });
    void qc.invalidateQueries({ queryKey: qk.onboarding });
  };
}

export function useCreateOrder() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (body: OrderCreate) => ordersService.create(body),
    onSuccess: (o) => {
      toastSuccess(
        `${o.side} order ${o.status.toLowerCase().replace(/_/g, " ")}`,
        `${o.quantity} × ${o.symbol} routed in ${o.trading_mode} mode`,
      );
    },
    onError: toastError,
    // A risk/broker rejection (400) still records an order: refresh either way.
    onSettled: invalidate,
  });
}

export function useCancelOrder() {
  const invalidate = useInvalidateOrders();
  return useMutation({
    mutationFn: (id: string) => ordersService.cancel(id),
    onSuccess: (o) => toastSuccess("Order cancelled", `${o.side} ${o.quantity} × ${o.symbol}`),
    onError: toastError,
    onSettled: invalidate,
  });
}
