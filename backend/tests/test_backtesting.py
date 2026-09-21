from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from app.backtesting.engine import BacktestConfig, BacktestEngine
from app.backtesting.metrics import max_drawdown, sharpe_ratio, trade_stats
from app.domain.enums import ExitReason, OrderSide, PositionSide, SignalType
from app.domain.types import Candle, SignalResult
from app.strategies.base import Strategy
from app.trading.charges import ChargesCalculator, ChargesConfig
from tests.conftest import make_candles

NO_CHARGES = ChargesConfig(0, 0, 0, 0, 0, 0, 0)


class ScriptedStrategy(Strategy):
    """Emits a fixed signal per bar index so fills are fully predictable."""

    strategy_type = "SCRIPTED"  # type: ignore[assignment]
    display_name = "Scripted"
    description = ""
    parameter_specs = ()

    def __init__(self, script: dict[int, SignalType]) -> None:
        super().__init__({})
        self.script = script
        self.bar = -1

    @property
    def lookback_bars(self) -> int:
        return 1

    def generate_signal(self, market_data: Sequence[Candle]) -> SignalResult:
        self.bar += 1
        return SignalResult(self.script.get(self.bar, SignalType.HOLD), market_data[-1].close)


def run(closes, script, **config):
    base = dict(
        symbol="TEST",
        initial_capital=100_000,
        risk_per_trade=0.01,
        stop_loss_pct=0.05,
        slippage_pct=0.0,
        charges=NO_CHARGES,
    )
    return BacktestEngine(ScriptedStrategy(script), BacktestConfig(**(base | config))).run(
        make_candles(closes, spread=0.0)
    )


class TestPnl:
    def test_winning_long_trade(self):
        # BUY signal on bar 1 close -> filled at bar 2 open (=100). SELL on bar 3 -> filled at bar 4 open (=110).
        result = run([100, 100, 100, 110, 110, 110], {1: SignalType.BUY, 3: SignalType.SELL})
        (trade,) = result.trades
        assert (trade.side, trade.entry_price, trade.exit_price, trade.exit_reason) == (
            PositionSide.LONG,
            100,
            110,
            ExitReason.SIGNAL,
        )
        assert trade.quantity == 200  # risk 1,000 / (100 * 5%) = 200
        assert trade.net_pnl == 2_000
        assert result.metrics["final_capital"] == 102_000 and result.metrics["net_pnl"] == 2_000
        assert result.metrics["total_return_pct"] == 2.0

    def test_no_lookahead_signal_bar_close_is_not_the_fill(self):
        result = run([100, 100, 105, 120, 120], {1: SignalType.BUY})
        assert result.trades[0].entry_price == 100  # open of bar 2 == close of bar 1, not bar 2's close (105)

    def test_short_trade_when_allowed(self):
        result = run([100, 100, 100, 90, 90, 90], {1: SignalType.SELL, 3: SignalType.BUY}, allow_short=True)
        assert result.trades[0].side is PositionSide.SHORT and result.trades[0].net_pnl == 2_000
        assert run([100, 100, 100, 90, 90], {1: SignalType.SELL}).trades == []  # shorting disabled by default

    def test_stop_loss_exit(self):
        result = run([100, 100, 100, 90, 90], {1: SignalType.BUY})
        (trade,) = result.trades
        assert (
            trade.exit_reason is ExitReason.STOP_LOSS and trade.exit_price == 95 and trade.net_pnl == -1_000
        )

    def test_gap_through_stop_fills_at_open(self):
        candles = make_candles([100, 100, 100], spread=0.0) + [
            Candle(datetime(2026, 1, 5, 5, 0, tzinfo=UTC), 80, 82, 78, 81, 1000)
        ]
        engine = BacktestEngine(
            ScriptedStrategy({1: SignalType.BUY}),
            BacktestConfig("TEST", 100_000, 0.01, 0.05, slippage_pct=0, charges=NO_CHARGES),
        )
        assert engine.run(candles).trades[0].exit_price == 80

    def test_target_exit_and_stop_takes_priority_when_both_hit(self):
        assert (
            run([100, 100, 100, 111, 111], {1: SignalType.BUY}, target_pct=0.10).trades[0].exit_reason
            is ExitReason.TARGET
        )
        both = make_candles([100, 100, 100], spread=0.0) + [
            Candle(datetime(2026, 1, 5, 5, 0, tzinfo=UTC), 100, 115, 90, 100, 1000)
        ]
        engine = BacktestEngine(
            ScriptedStrategy({1: SignalType.BUY}),
            BacktestConfig("TEST", 100_000, 0.01, 0.05, 0.10, slippage_pct=0, charges=NO_CHARGES),
        )
        assert engine.run(both).trades[0].exit_reason is ExitReason.STOP_LOSS

    def test_open_position_is_closed_at_end_of_data(self):
        result = run([100, 100, 100, 104], {1: SignalType.BUY})
        assert (
            result.trades[0].exit_reason is ExitReason.END_OF_DATA
            and result.metrics["final_capital"] == 100_800
        )


class TestCosts:
    def test_slippage_worsens_both_fills(self):
        result = run(
            [100, 100, 100, 110, 110, 110], {1: SignalType.BUY, 3: SignalType.SELL}, slippage_pct=0.01
        )
        trade = result.trades[0]
        assert trade.entry_price == 101 and trade.exit_price == pytest.approx(108.9)
        assert trade.net_pnl < 2_000 and result.metrics["total_slippage"] > 0

    def test_charges_reduce_net_pnl(self):
        charges = ChargesConfig(
            brokerage_per_order=20,
            brokerage_pct=0,
            stt_sell_pct=0,
            exchange_txn_pct=0,
            sebi_pct=0,
            stamp_duty_buy_pct=0,
            gst_pct=0,
        )
        result = run([100, 100, 100, 110, 110, 110], {1: SignalType.BUY, 3: SignalType.SELL}, charges=charges)
        trade = result.trades[0]
        assert (trade.gross_pnl, trade.charges, trade.net_pnl) == (2_000, 40, 1_960)
        assert result.metrics["total_charges"] == 40 and result.metrics["final_capital"] == 101_960

    def test_costs_turn_a_flat_trade_into_a_loss(self):
        result = run(
            [100] * 6, {1: SignalType.BUY, 3: SignalType.SELL}, charges=ChargesConfig(), slippage_pct=0.0005
        )
        assert result.metrics["net_pnl"] < 0

    def test_charges_calculator_breakdown(self):
        calc = ChargesCalculator(ChargesConfig(20, 0.0003, 0.00025, 0.0000297, 0.000001, 0.00003, 0.18))
        turnover = 100_000
        buy, sell = calc.compute(OrderSide.BUY, 1_000, 100), calc.compute(OrderSide.SELL, 1_000, 100)
        taxable = (
            20 + turnover * 0.0000297 + turnover * 0.000001
        )  # brokerage capped at 20 (0.03% would be 30)
        assert buy == pytest.approx(taxable * 1.18 + turnover * 0.00003, abs=0.01)
        assert sell == pytest.approx(taxable * 1.18 + turnover * 0.00025, abs=0.01)
        assert calc.brokerage(10_000) == pytest.approx(3.0)  # small order: percentage below the cap


class _T:
    def __init__(self, net_pnl: float) -> None:
        self.net_pnl = net_pnl


class TestMetrics:
    def test_win_rate_profit_factor_and_extremes(self):
        stats = trade_stats([_T(300), _T(-100), _T(200), _T(-100)])
        assert (stats.total_trades, stats.winning_trades, stats.losing_trades, stats.win_rate) == (
            4,
            2,
            2,
            50.0,
        )
        assert (stats.gross_profit, stats.gross_loss, stats.net_pnl, stats.profit_factor) == (
            500,
            -200,
            300,
            2.5,
        )
        assert (stats.average_trade, stats.largest_win, stats.largest_loss) == (75, 300, -100)

    def test_no_trades_and_no_losses(self):
        assert trade_stats([]).win_rate == 0 and trade_stats([]).profit_factor is None
        assert trade_stats([_T(10)]).profit_factor is None

    def test_max_drawdown(self):
        amount, pct = max_drawdown([100, 120, 90, 110, 80, 130])
        assert amount == 40 and pct == pytest.approx(33.3333, abs=1e-3)
        assert max_drawdown([100, 110, 120]) == (0, 0)

    def test_engine_reports_drawdown(self):
        result = run([100, 100, 100, 110, 100, 100], {1: SignalType.BUY})
        assert result.metrics["max_drawdown"] == 2_000
        assert min(p.drawdown for p in result.equity_curve) == -2_000

    def test_sharpe_needs_enough_daily_observations(self):
        start = datetime(2026, 1, 1, 6, 0, tzinfo=UTC)
        few = [start + timedelta(days=i) for i in range(10)]
        assert sharpe_ratio(few, [100 + i for i in range(10)]) is None
        many = [start + timedelta(days=i) for i in range(60)]
        equity = [100 * (1.001**i) * (1.002 if i % 2 else 0.999) for i in range(60)]
        assert sharpe_ratio(many, equity) > 0
        assert sharpe_ratio(many, [100.0] * 60) is None  # zero variance
