"use client";

import { useQuery } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { guideService } from "@/services/guide";
import type { ReviewRequest } from "@/types";

/** Getting-started checklist. Refetches on window focus so it updates after doing a step elsewhere. */
export function useOnboarding() {
  return useQuery({
    queryKey: qk.onboarding,
    queryFn: guideService.onboarding,
    refetchOnWindowFocus: true,
    staleTime: 5_000,
  });
}

/** Review of a saved strategy (GET /strategies/{id}/review). */
export function useStrategyReview(id: string | null) {
  return useQuery({
    queryKey: qk.strategyReview(id ?? ""),
    queryFn: () => guideService.reviewStrategy(id as string),
    enabled: !!id,
    staleTime: 10_000,
  });
}

/** Review of a draft setup (POST /strategies/review); pass null while the form is not valid enough. */
export function useDraftReview(request: ReviewRequest | null) {
  return useQuery({
    queryKey: qk.strategyReviewDraft(request as ReviewRequest),
    queryFn: () => guideService.reviewDraft(request as ReviewRequest),
    enabled: request !== null,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
    retry: false,
  });
}
