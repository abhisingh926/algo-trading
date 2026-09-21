"""Strategy worker path: candles -> signal -> sizing -> risk -> paper order -> position -> exit."""

from datetime import timedelta

from app.domain.enums import OrderSource, SignalStatus, SignalType, StrategyStatus
from app.domain.types import Candle
from app.schemas.strategy import StrategyCreate
from app.services.factory import Services
from app.trading.engine import TradingEngine
from app.utils.time import floor_time, utcnow


def live_candles(closes: list[float], minutes: int = 5) -> list[Candle]:
    """Closed bars ending at the most recent completed bar boundary."""
    last_start = floor_time(utcnow(), minutes) - timedelta(minutes=minutes)
    first = last_start - timedelta(minutes=minutes * (len(closes) - 1))
    out, prev = [], closes[0]
    for i, close in enumerate(closes):
        out.append(
            Candle(
                first + timedelta(minutes=minutes * i),
                prev,
                max(prev, close) + 0.5,
                min(prev, close) - 0.5,
                close,
                1000,
            )
        )
        prev = close
    return out


async def make_strategy(services: Services, **overrides):
    body = StrategyCreate(
        **(
            {
                "name": "EMA Intraday",
                "strategy_type": "EMA_CROSSOVER",
                "symbol": "RELIANCE",
                "timeframe": "5m",
                "capital": 100_000,
                "risk_per_trade": 0.01,
                "stop_loss_pct": 0.01,
                "target_pct": 0.02,
                "parameters": {"fast_period": 3, "slow_period": 6},
            }
            | overrides
        )
    )
    strategy = await services.strategies.create(None, body.model_dump())
    return await services.strategies.start(strategy.id)


UP_CROSS = [100.0] * 10 + [99, 98, 97, 96, 95, 96, 98, 101]  # last bar is the bullish crossover
DOWN_CROSS = [100.0] * 10 + [101, 102, 103, 100, 96]


async def test_buy_signal_creates_sized_order_and_position(services, market_data):
    strategy = await make_strategy(services)
    market_data.candles["RELIANCE"] = live_candles(UP_CROSS)
    market_data.set_price("RELIANCE", 101)

    signal = await services.trading.evaluate_strategy(strategy)
    assert signal.signal_type is SignalType.BUY and signal.status is SignalStatus.EXECUTED

    (order,) = await services.orders.list_orders()
    # risk 1% of 1L = 1,000; stop 1% of 101 = 1.01/share -> 990 shares, capped by capital: floor(100000/101) = 990
    assert (order.source, order.quantity, order.stop_loss, order.target) == (
        OrderSource.STRATEGY,
        990,
        99.99,
        103.02,
    )
    (position,) = await services.positions.list_positions("open")
    assert (position.strategy_id, position.quantity, position.stop_loss) == (strategy.id, 990, 99.99)
    assert signal.order_id == order.id

    # same candle again -> idempotent, no duplicate order
    assert await services.trading.evaluate_strategy(strategy) is None
    assert len(await services.orders.list_orders()) == 1


async def test_sell_signal_closes_the_position_and_books_a_trade(services, market_data):
    strategy = await make_strategy(services)
    market_data.candles["RELIANCE"] = live_candles(UP_CROSS)
    market_data.set_price("RELIANCE", 101)
    await services.trading.evaluate_strategy(strategy)

    strategy.last_candle_at = None
    market_data.candles["RELIANCE"] = live_candles(DOWN_CROSS)
    market_data.set_price("RELIANCE", 96)
    signal = await services.trading.evaluate_strategy(strategy)
    assert signal.signal_type is SignalType.SELL and signal.status is SignalStatus.EXECUTED
    assert await services.positions.list_positions("open") == []
    (trade,) = await services.trades.list_trades()
    assert trade.strategy_id == strategy.id and trade.net_pnl < 0 and trade.exit_reason.value == "SIGNAL"

    read = await services.strategies.to_read(strategy)
    assert (
        read.stats.trades == 1
        and read.stats.total_pnl == round(trade.net_pnl, 2)
        and read.stats.win_rate == 0
    )


async def test_sell_signal_without_position_is_ignored_when_shorting_disabled(services, market_data):
    strategy = await make_strategy(services)
    market_data.candles["RELIANCE"] = live_candles(DOWN_CROSS)
    signal = await services.trading.evaluate_strategy(strategy)
    assert signal.status is SignalStatus.IGNORED and await services.orders.list_orders() == []


async def test_risk_rejection_marks_signal_rejected(services, market_data):
    await services.risk.update_config({"max_order_value": 1_000})
    strategy = await make_strategy(services)
    market_data.candles["RELIANCE"] = live_candles(UP_CROSS)
    market_data.set_price("RELIANCE", 101)
    signal = await services.trading.evaluate_strategy(strategy)
    # the sizer respects max_order_value (9 shares), so the order passes; shrink further to force a reject
    assert signal.status is SignalStatus.EXECUTED and (await services.orders.list_orders())[0].quantity == 9

    await services.risk.update_config({"max_open_positions": 1})
    other = await make_strategy(services, name="EMA 2", symbol="INFY")
    market_data.candles["INFY"] = live_candles(UP_CROSS)
    market_data.set_price("INFY", 101)
    rejected = await services.trading.evaluate_strategy(other)
    assert rejected.status is SignalStatus.REJECTED and "Maximum open positions" in rejected.status_reason


async def test_engine_cycles_run_end_to_end(container, market_data):
    engine = TradingEngine(container)
    async with engine.unit_of_work() as services:
        strategy_id = (await make_strategy(services)).id
    market_data.candles["RELIANCE"] = live_candles(UP_CROSS)
    market_data.set_price("RELIANCE", 101)

    assert await engine.run_strategy_cycle() == 1
    market_data.set_price("RELIANCE", 104)  # above the 103.02 target
    await engine.run_market_data_cycle()
    await engine.run_order_cycle()

    async with engine.unit_of_work() as services:
        assert await services.positions.list_positions("open") == []
        (trade,) = await services.trades.list_trades()
        assert trade.exit_reason.value == "TARGET" and trade.net_pnl > 0
        summary = await services.pnl.summary()
        assert summary.trades_today == 1 and summary.realized_pnl_today == round(trade.net_pnl, 2)
        series = await services.pnl.series(30)
        assert len(series.daily) == 1 and len(series.equity_curve) >= 1
        events = {e.event_type for e in await services.events.list_events(limit=200)}
        assert {
            "strategy_started",
            "signal_generated",
            "risk_check_passed",
            "order_submitted",
            "order_filled",
            "position_opened",
            "position_closed",
        } <= events

    # halted system: strategies are not evaluated
    async with engine.unit_of_work() as services:
        await services.trading.set_kill_switch(True, "test")
    assert await engine.run_strategy_cycle() == 0
    async with engine.unit_of_work() as services:
        assert (await services.strategies.get(strategy_id)).status is StrategyStatus.STOPPED


async def test_failing_strategy_is_marked_error_not_crashing_the_worker(container, market_data, monkeypatch):
    engine = TradingEngine(container)
    async with engine.unit_of_work() as services:
        strategy_id = (await make_strategy(services)).id

    async def boom(*_a, **_k):
        raise RuntimeError("feed exploded")

    monkeypatch.setattr(market_data, "get_historical_data", boom)
    assert await engine.run_strategy_cycle() == 0
    async with engine.unit_of_work() as services:
        strategy = await services.strategies.get(strategy_id)
        assert strategy.status is StrategyStatus.ERROR and "feed exploded" in strategy.last_error
