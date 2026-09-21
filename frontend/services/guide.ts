import { api } from "@/lib/api";
import type { Onboarding, ReviewRequest, StrategyReview } from "@/types";

export const guideService = {
  onboarding: () => api.get<Onboarding>("/guide/onboarding"),
  /** Reviews a draft setup: works before the strategy is saved. */
  reviewDraft: (body: ReviewRequest) => api.post<StrategyReview>("/strategies/review", body),
  /** Reviews a saved strategy, including its latest backtest and paper record. */
  reviewStrategy: (id: string) => api.get<StrategyReview>(`/strategies/${id}/review`),
};
