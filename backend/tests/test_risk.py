import pytest

from app.risk.limits import OrderIntent, RiskContext, RiskLimits
from app.risk.position_sizer import PositionSizer
from app.risk.risk_manager import RiskManager

LIMITS = RiskLimits(
    max_risk_per_trade=0.01,
    max_daily_loss=5_000,
    max_trades_per_day=20,
    max_open_positions=5,
    max_position_size=1_000,
    max_order_value=300_000,
    max_consecutive_losses=3,
    max_strategy_drawdown=0.10,
)


def ctx(**overrides) -> RiskContext:
    base = dict(
        capital=500_000,
        available_capital=500_000,
        daily_pnl=0,
        trades_today=0,
        open_positions=0,
        consecutive_losses=0,
    )
    return RiskContext(**(base | overrides))


def evaluate(intent: OrderIntent, **overrides):
    return RiskManager(LIMITS).evaluate(intent, ctx(**overrides))


GOOD = OrderIntent("RELIANCE", quantity=250, price=1_000, stop_loss=980)  # risk 5,000 = exactly 1%


class TestRiskManager:
    def test_approves_order_within_all_limits(self):
        decision = evaluate(GOOD)
        assert decision.approved and decision.violations == ()

    def test_maximum_risk_per_trade(self):
        decision = evaluate(OrderIntent("RELIANCE", 260, 1_000, stop_loss=980))  # risk 5,200 > 5,000
        assert not decision.approved and "maximum risk per trade" in decision.reason

    def test_risk_per_trade_uses_strategy_capital_when_present(self):
        decision = evaluate(GOOD, strategy_capital=100_000)  # 1% of 1L = 1,000 < 5,000
        assert not decision.approved and "maximum risk per trade" in decision.reason

    def test_daily_loss_limit_blocks_new_entries(self):
        assert evaluate(GOOD, daily_pnl=-4_999).approved
        decision = evaluate(GOOD, daily_pnl=-5_000)
        assert not decision.approved and "Daily loss limit" in decision.reason

    def test_maximum_trades_per_day(self):
        assert evaluate(GOOD, trades_today=19).approved
        assert "Maximum trades per day" in evaluate(GOOD, trades_today=20).reason

    def test_maximum_open_positions(self):
        assert "Maximum open positions" in evaluate(GOOD, open_positions=5).reason

    def test_maximum_position_size(self):
        assert "maximum position size" in evaluate(OrderIntent("ITC", 1_001, 100)).reason

    def test_maximum_order_value(self):
        assert "maximum order value" in evaluate(OrderIntent("RELIANCE", 301, 1_000)).reason

    def test_available_capital(self):
        assert "available capital" in evaluate(GOOD, available_capital=100_000).reason

    def test_maximum_consecutive_losses(self):
        assert "consecutive losses" in evaluate(GOOD, consecutive_losses=3).reason

    def test_maximum_strategy_drawdown(self):
        decision = evaluate(
            OrderIntent("RELIANCE", 50, 1_000, 980), strategy_capital=100_000, strategy_drawdown=10_000
        )
        assert "drawdown" in decision.reason

    def test_kill_switch_blocks_entries(self):
        assert "Kill switch" in evaluate(GOOD, kill_switch_active=True).reason

    def test_reducing_orders_pass_even_when_everything_is_breached(self):
        exit_intent = OrderIntent("RELIANCE", 250, 1_000, is_reducing=True)
        decision = evaluate(
            exit_intent, kill_switch_active=True, daily_pnl=-50_000, trades_today=99, open_positions=99
        )
        assert decision.approved

    def test_all_violations_are_reported_together(self):
        decision = evaluate(GOOD, daily_pnl=-9_000, trades_today=25)
        assert len(decision.violations) == 2

    def test_invalid_quantity_and_price(self):
        assert not evaluate(OrderIntent("RELIANCE", 0, 1_000)).approved
        assert not evaluate(OrderIntent("RELIANCE", 10, 0)).approved


class TestPositionSizer:
    def test_spec_example(self):
        """Capital 5,00,000, risk 1%, entry 1,000, stop 980 -> 250 shares."""
        result = PositionSizer().size(500_000, 0.01, 1_000, 980)
        assert (result.quantity, result.risk_per_share, result.max_risk_amount, result.risk_amount) == (
            250,
            20,
            5_000,
            5_000,
        )
        assert result.capped_by is None

    def test_short_side_uses_absolute_distance(self):
        assert PositionSizer().size(500_000, 0.01, 1_000, 1_020).quantity == 250

    def test_quantity_is_floored(self):
        assert (
            PositionSizer().size(100_000, 0.01, 333, 330).quantity == 300
        )  # 1000/3 = 333.3 -> capital cap 300
        assert PositionSizer().size(1_000_000, 0.01, 333, 326).quantity == 1_428  # 10000/7 = 1428.57

    def test_capped_by_max_position_size(self):
        result = PositionSizer(max_position_size=100).size(500_000, 0.01, 1_000, 980)
        assert (result.quantity, result.capped_by, result.risk_amount) == (100, "max_position_size", 2_000)

    def test_capped_by_max_order_value(self):
        result = PositionSizer(max_order_value=50_000).size(500_000, 0.01, 1_000, 980)
        assert (result.quantity, result.capped_by) == (50, "max_order_value")

    def test_never_uses_leverage(self):
        result = PositionSizer().size(100_000, 0.02, 1_000, 999)  # raw = 2000 shares = 20L notional
        assert (result.quantity, result.capped_by) == (100, "available_capital")

    def test_respects_available_capital(self):
        assert PositionSizer().size(500_000, 0.01, 1_000, 980, available_capital=120_000).quantity == 120

    def test_lot_size_rounding(self):
        assert PositionSizer().size(500_000, 0.01, 1_000, 980, lot_size=75).quantity == 225

    @pytest.mark.parametrize(
        "args", [(0, 0.01, 100, 99), (1000, 0, 100, 99), (1000, 0.01, 100, 100), (1000, 1.5, 100, 99)]
    )
    def test_invalid_inputs(self, args):
        with pytest.raises(ValueError):
            PositionSizer().size(*args)
