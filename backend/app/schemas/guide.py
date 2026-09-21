from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import StrategyType, Timeframe, TradingMode


class ReviewRequest(BaseModel):
    """A strategy setup to review. Used by the builder before the strategy is saved."""

    strategy_id: str | None = Field(
        default=None, description="Existing strategy, to include its backtest and paper record"
    )
    strategy_type: StrategyType
    symbol: str
    exchange: str = "NSE"
    timeframe: Timeframe
    capital: float = Field(gt=0)
    risk_per_trade: float = Field(gt=0, le=1)
    stop_loss_pct: float = Field(gt=0, lt=1)
    target_pct: float | None = Field(default=None, gt=0)
    allow_short: bool = False
    trading_mode: TradingMode = TradingMode.PAPER
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol", "exchange")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class ReviewCheck(BaseModel):
    key: str
    category: str
    severity: str
    title: str
    detail: str
    suggestion: str | None = None


class ReviewCounts(BaseModel):
    good: int
    info: int
    warn: int
    risk: int


class StrategyReview(BaseModel):
    verdict: str
    summary: str
    counts: ReviewCounts
    checks: list[ReviewCheck]
    has_backtest: bool
    backtest_id: str | None = None
    disclaimer: str = (
        "Advice based on common good-practice guidelines. It does not predict profit, "
        "and you decide whether to run the strategy."
    )


class OnboardingStep(BaseModel):
    key: str
    title: str
    description: str
    href: str
    done: bool
    optional: bool = False


class Onboarding(BaseModel):
    steps: list[OnboardingStep]
    completed: int
    total: int
    percent: int
    next_step: str | None
    all_done: bool
