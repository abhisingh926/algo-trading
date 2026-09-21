from fastapi import APIRouter

from app.core.dependencies import ServicesDep
from app.schemas.common import ApiResponse, ok
from app.schemas.guide import Onboarding, ReviewRequest, StrategyReview

router = APIRouter(tags=["Guide"])


@router.get("/guide/onboarding", response_model=ApiResponse[Onboarding])
async def onboarding(services: ServicesDep):
    """Getting-started checklist, derived from what the user has actually done."""
    return ok(await services.guide.onboarding(), "Onboarding progress")


@router.post("/strategies/review", response_model=ApiResponse[StrategyReview])
async def review_draft(body: ReviewRequest, services: ServicesDep):
    """Good-practice review of a strategy setup (used live by the strategy builder). Advisory only."""
    review = await services.guide.review(body)
    return ok(review, "Strategy review", description=review.summary)


@router.get("/strategies/{strategy_id}/review", response_model=ApiResponse[StrategyReview])
async def review_saved(strategy_id: str, services: ServicesDep):
    review = await services.guide.review_saved(strategy_id)
    return ok(review, "Strategy review", description=review.summary)
