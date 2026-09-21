"""Pre-trade risk gate. Pure logic: no I/O, fully unit-testable."""

from __future__ import annotations

from app.risk.limits import OrderIntent, RiskContext, RiskDecision, RiskLimits

_EPS = 1e-6


class RiskManager:
    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits

    def evaluate(self, intent: OrderIntent, ctx: RiskContext) -> RiskDecision:
        violations: list[str] = []
        if intent.quantity <= 0:
            violations.append("Order quantity must be positive")
        if intent.price <= 0:
            violations.append("No valid price available for risk evaluation")

        if intent.is_reducing:
            # Exits must always be possible (even when halted), otherwise risk could not be reduced.
            return RiskDecision(not violations, tuple(violations))

        if ctx.kill_switch_active:
            violations.append("Kill switch is active - new orders are blocked")
        violations.extend(self._order_limits(intent, ctx))
        violations.extend(self._account_limits(ctx))
        return RiskDecision(not violations, tuple(violations))

    def _order_limits(self, intent: OrderIntent, ctx: RiskContext) -> list[str]:
        limits, out = self.limits, []
        if intent.quantity > limits.max_position_size:
            out.append(f"Quantity {intent.quantity} exceeds maximum position size {limits.max_position_size}")
        if intent.value > limits.max_order_value + _EPS:
            out.append(
                f"Order value ₹{intent.value:,.2f} exceeds maximum order value ₹{limits.max_order_value:,.2f}"
            )
        if intent.value > ctx.available_capital + _EPS:
            out.append(
                f"Order value ₹{intent.value:,.2f} exceeds available capital ₹{ctx.available_capital:,.2f}"
            )
        risk = intent.risk_amount
        if risk is not None:
            allowed = limits.max_risk_per_trade * (ctx.strategy_capital or ctx.capital)
            if risk > allowed + _EPS:
                out.append(f"Trade risk ₹{risk:,.2f} exceeds maximum risk per trade ₹{allowed:,.2f}")
        return out

    def _account_limits(self, ctx: RiskContext) -> list[str]:
        limits, out = self.limits, []
        if ctx.daily_pnl <= -limits.max_daily_loss:
            out.append(
                f"Daily loss limit reached (₹{ctx.daily_pnl:,.2f} vs limit -₹{limits.max_daily_loss:,.2f})"
            )
        if ctx.trades_today >= limits.max_trades_per_day:
            out.append(f"Maximum trades per day reached ({limits.max_trades_per_day})")
        if ctx.open_positions >= limits.max_open_positions:
            out.append(f"Maximum open positions reached ({limits.max_open_positions})")
        if ctx.consecutive_losses >= limits.max_consecutive_losses:
            out.append(f"Maximum consecutive losses reached ({limits.max_consecutive_losses})")
        if (
            ctx.strategy_capital
            and ctx.strategy_drawdown >= limits.max_strategy_drawdown * ctx.strategy_capital
        ):
            out.append(
                f"Strategy drawdown ₹{ctx.strategy_drawdown:,.2f} exceeds "
                f"{limits.max_strategy_drawdown:.1%} of strategy capital"
            )
        return out
