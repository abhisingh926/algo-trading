from app.trading.engine import TradingEngine
from app.workers.base import PeriodicWorker

NAME = "strategy_worker"


def build(engine: TradingEngine) -> PeriodicWorker:
    """Evaluates RUNNING strategies whenever a new candle has closed."""
    c = engine.container
    return PeriodicWorker(NAME, c.settings.strategy_poll_seconds, engine.run_strategy_cycle, c.workers)
