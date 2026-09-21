from __future__ import annotations

from typing import Any

from app.domain.enums import StrategyType
from app.strategies.base import Strategy, StrategyConfigError
from app.strategies.breakout import BreakoutStrategy
from app.strategies.ema_crossover import EmaCrossoverStrategy
from app.strategies.vwap import VwapStrategy

STRATEGY_REGISTRY: dict[StrategyType, type[Strategy]] = {
    cls.strategy_type: cls for cls in (EmaCrossoverStrategy, VwapStrategy, BreakoutStrategy)
}


def create_strategy(strategy_type: StrategyType | str, parameters: dict[str, Any] | None = None) -> Strategy:
    try:
        cls = STRATEGY_REGISTRY[StrategyType(strategy_type)]
    except (KeyError, ValueError) as exc:
        raise StrategyConfigError(f"Unknown strategy type: {strategy_type}") from exc
    return cls(parameters)


def describe_strategies() -> list[dict[str, Any]]:
    return [cls.describe() for cls in STRATEGY_REGISTRY.values()]
