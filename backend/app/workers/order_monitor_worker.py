from app.trading.engine import TradingEngine
from app.workers.base import PeriodicWorker

NAME = "order_monitor_worker"


def build(engine: TradingEngine) -> PeriodicWorker:
    """Tracks working orders (fills, partial fills, cancels), protective exits and equity snapshots."""
    c = engine.container
    return PeriodicWorker(NAME, c.settings.order_monitor_poll_seconds, engine.run_order_cycle, c.workers)
