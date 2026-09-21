import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";

export const POLL_FAST_MS = 5_000;
export const POLL_SLOW_MS = 15_000;

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 2_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.code >= 400 && error.code < 500) return false;
          return failureCount < 1;
        },
      },
      mutations: { retry: false },
    },
  });
}
