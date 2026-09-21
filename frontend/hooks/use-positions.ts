"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { POLL_FAST_MS } from "@/lib/query-client";
import { toastError, toastSuccess } from "@/lib/toast";
import { positionsService } from "@/services/positions";
import type { PositionStatusFilter, PositionUpdate } from "@/types";

export function usePositions(status: PositionStatusFilter = "open") {
  return useQuery({
    queryKey: qk.positionsList(status),
    queryFn: () => positionsService.list(status),
    refetchInterval: POLL_FAST_MS,
    placeholderData: (prev) => prev,
  });
}

function useInvalidatePositions() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: qk.positions });
    void qc.invalidateQueries({ queryKey: qk.orders });
    void qc.invalidateQueries({ queryKey: qk.trades });
    void qc.invalidateQueries({ queryKey: qk.dashboard });
    void qc.invalidateQueries({ queryKey: qk.risk });
    void qc.invalidateQueries({ queryKey: qk.onboarding });
  };
}

export function useUpdatePosition() {
  const invalidate = useInvalidatePositions();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: PositionUpdate }) =>
      positionsService.update(id, body),
    onSuccess: (p) => {
      toastSuccess("Position updated", `${p.symbol}: stop loss / target saved`);
      invalidate();
    },
    onError: toastError,
  });
}

export function useClosePosition() {
  const invalidate = useInvalidatePositions();
  return useMutation({
    mutationFn: (id: string) => positionsService.close(id),
    onSuccess: (o) =>
      toastSuccess("Exit order placed", `${o.side} ${o.quantity} × ${o.symbol} (${o.status})`),
    onError: toastError,
    onSettled: invalidate,
  });
}
