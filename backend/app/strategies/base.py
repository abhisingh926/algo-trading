"""Strategy abstraction. Strategies are pure: candles in, signal out. No broker, DB or order logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, ClassVar

from app.domain.enums import StrategyType
from app.domain.types import Candle, SignalResult


class StrategyConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str
    label: str
    type: str  # "int" | "float"
    default: float
    min: float
    max: float
    description: str = ""

    def coerce(self, raw: Any) -> float | int:
        try:
            value = int(raw) if self.type == "int" else float(raw)
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"Parameter '{self.key}' must be a {self.type}") from exc
        if self.type == "int" and float(raw) != value:
            raise StrategyConfigError(f"Parameter '{self.key}' must be a whole number")
        if not self.min <= value <= self.max:
            raise StrategyConfigError(f"Parameter '{self.key}' must be between {self.min} and {self.max}")
        return value


class Strategy(ABC):
    strategy_type: ClassVar[StrategyType]
    display_name: ClassVar[str]
    description: ClassVar[str]
    parameter_specs: ClassVar[tuple[ParameterSpec, ...]]

    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        self.params = self.validate_parameters(parameters or {})
        self.validate()

    @classmethod
    def validate_parameters(cls, parameters: dict[str, Any]) -> dict[str, float | int]:
        specs = {spec.key: spec for spec in cls.parameter_specs}
        unknown = set(parameters) - set(specs)
        if unknown:
            raise StrategyConfigError(
                f"Unknown parameter(s) for {cls.strategy_type.value}: {', '.join(sorted(unknown))}"
            )
        return {key: spec.coerce(parameters.get(key, spec.default)) for key, spec in specs.items()}

    def validate(self) -> None:  # noqa: B027 - optional hook for cross-parameter checks
        pass

    @property
    @abstractmethod
    def lookback_bars(self) -> int:
        """How many most-recent bars `generate_signal` needs to produce a stable result."""

    @abstractmethod
    def generate_signal(self, market_data: Sequence[Candle]) -> SignalResult:
        """Evaluate the LAST candle in `market_data` (all candles must be closed bars)."""

    @classmethod
    def describe(cls) -> dict[str, Any]:
        return {
            "type": cls.strategy_type.value,
            "name": cls.display_name,
            "description": cls.description,
            "parameters": [asdict(spec) for spec in cls.parameter_specs],
        }
