from app.trading.engine import TradingEngine
from app.workers.base import PeriodicWorker

NAME = "market_data_worker"


def build(engine: TradingEngine) -> PeriodicWorker:
    """Keeps the quote cache warm and open positions marked to market."""
    c = engine.container
    return PeriodicWorker(NAME, c.settings.market_data_poll_seconds, engine.run_market_data_cycle, c.workers)
