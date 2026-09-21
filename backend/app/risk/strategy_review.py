"""Best-practice review of a strategy setup. Pure logic: no I/O, fully unit-testable.

The output is ADVICE, never a gate: the platform still lets the user start a strategy the review dislikes.
Thresholds are widely used guidelines for retail systematic trading, not guarantees of profit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.enums import StrategyType, Timeframe, TradingMode

# --- guideline thresholds -------------------------------------------------------------------------
RISK_GOOD_PCT = 1.0  # risk per trade at or below this is the common guideline
RISK_MAX_PCT = 2.0  # above this is aggressive
RISK_DANGER_PCT = 5.0
STOP_TIGHT = 0.003  # 0.3%: inside normal intraday noise
STOP_WIDE = 0.05
ROUND_TRIP_COST = 0.001  # rough all-in cost of one round trip (brokerage, taxes, fees) as a fraction of value
RR_GOOD = 1.5
MIN_TRADES_MEANINGFUL = 30
MIN_TRADES_GOOD = 100
MIN_BACKTEST_DAYS = 30
GOOD_BACKTEST_DAYS = 90
PROFIT_FACTOR_GOOD = 1.3
DRAWDOWN_WARN_PCT = 10.0
DRAWDOWN_RISK_PCT = 20.0
COST_SHARE_WARN = 0.5  # charges above half of gross profit
MIN_PAPER_TRADES_BEFORE_REAL_MONEY = 30


class Severity(StrEnum):
    GOOD = "GOOD"
    INFO = "INFO"
    WARN = "WARN"
    RISK = "RISK"


class Verdict(StrEnum):
    RECOMMENDED = "RECOMMENDED"
    CAUTION = "CAUTION"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


@dataclass(frozen=True, slots=True)
class Check:
    key: str
    category: str  # configuration | backtest | safety
    severity: Severity
    title: str
    detail: str
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewInput:
    strategy_type: StrategyType
    timeframe: Timeframe
    capital: float
    risk_per_trade: float  # fractions: 0.01 = 1%
    stop_loss_pct: float
    target_pct: float | None
    allow_short: bool
    trading_mode: TradingMode
    parameters: dict[str, Any] = field(default_factory=dict)
    account_capital: float | None = None
    platform_max_risk_per_trade: float | None = None
    config_error: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestEvidence:
    trades: int
    net_pnl: float
    profit_factor: float | None
    max_drawdown_pct: float
    gross_profit: float
    total_charges: float
    data_source: str
    period_days: int
    sharpe_ratio: float | None
    stale: bool  # the strategy was edited after this backtest ran


@dataclass(frozen=True, slots=True)
class PaperRecord:
    trades: int
    net_pnl: float


@dataclass(frozen=True, slots=True)
class Review:
    verdict: Verdict
    summary: str
    checks: tuple[Check, ...]

    def count(self, severity: Severity) -> int:
        return sum(1 for c in self.checks if c.severity is severity)


def _pct(fraction: float) -> str:
    return f"{fraction * 100:.2f}".rstrip("0").rstrip(".") + "%"


# ---- configuration ---------------------------------------------------------------------------------
def _risk_per_trade(inp: ReviewInput) -> list[Check]:
    pct = inp.risk_per_trade * 100
    streak = 1 - (1 - inp.risk_per_trade) ** 10
    detail = f"Ten losing trades in a row would cost about {streak:.0%} of the strategy's capital."
    if pct <= RISK_GOOD_PCT:
        check = Check(
            "risk_per_trade",
            "configuration",
            Severity.GOOD,
            f"Risk per trade is {_pct(inp.risk_per_trade)}",
            detail,
        )
    elif pct <= RISK_MAX_PCT:
        check = Check(
            "risk_per_trade",
            "configuration",
            Severity.INFO,
            f"Risk per trade is {_pct(inp.risk_per_trade)}",
            detail + " Most guides suggest 1% or less.",
            "Consider lowering it to 1% until the strategy has a track record.",
        )
    elif pct <= RISK_DANGER_PCT:
        check = Check(
            "risk_per_trade",
            "configuration",
            Severity.WARN,
            f"Risk per trade is high ({_pct(inp.risk_per_trade)})",
            detail,
            "Keep risk per trade at 1% to 2% or less.",
        )
    else:
        check = Check(
            "risk_per_trade",
            "configuration",
            Severity.RISK,
            f"Risk per trade is very high ({_pct(inp.risk_per_trade)})",
            detail,
            "Lower it to 1%. A few bad trades could wipe out the account.",
        )
    out = [check]
    cap = inp.platform_max_risk_per_trade
    if cap is not None and inp.risk_per_trade > cap + 1e-9:
        out.append(
            Check(
                "risk_platform_cap",
                "configuration",
                Severity.INFO,
                "Platform risk limit will cap position size",
                f"The global limit is {_pct(cap)} per trade, so orders are sized to {_pct(cap)} instead of {_pct(inp.risk_per_trade)}.",
                "Change the limit on the Risk page, or lower this strategy's risk.",
            )
        )
    return out


def _stop_and_target(inp: ReviewInput) -> list[Check]:
    out: list[Check] = []
    stop = inp.stop_loss_pct
    if stop < STOP_TIGHT:
        out.append(
            Check(
                "stop_loss",
                "configuration",
                Severity.WARN,
                f"Stop loss is very tight ({_pct(stop)})",
                "Normal price noise will often hit a stop this close, so trades get stopped out before the idea can work.",
                "Try a stop of at least 0.5%, or one based on recent volatility.",
            )
        )
    elif stop > STOP_WIDE:
        out.append(
            Check(
                "stop_loss",
                "configuration",
                Severity.WARN,
                f"Stop loss is very wide ({_pct(stop)})",
                "A wide stop means a large loss per share, so position sizes become small and losses are slow to cut.",
                "Consider a tighter stop, or accept the smaller position size deliberately.",
            )
        )
    else:
        out.append(
            Check(
                "stop_loss",
                "configuration",
                Severity.GOOD,
                f"Stop loss is set ({_pct(stop)})",
                "Every entry gets a protective stop and the position size is calculated from it.",
            )
        )

    target = inp.target_pct
    if target is None:
        out.append(
            Check(
                "target",
                "configuration",
                Severity.WARN,
                "No profit target",
                "Trades exit only on a stop or an opposite signal, so profits can be given back.",
                "Set a target of at least 1.5 times the stop distance.",
            )
        )
        return out
    reward_risk = target / stop
    breakeven = 1 / (1 + reward_risk)
    detail = f"Reward to risk is {reward_risk:.1f}:1. You need to win more than {breakeven:.0%} of trades to break even, before costs."
    if reward_risk < 1:
        out.append(
            Check(
                "reward_risk",
                "configuration",
                Severity.WARN,
                "Reward is smaller than risk",
                detail,
                "Aim for a target at least equal to the stop, ideally 1.5 times.",
            )
        )
    elif reward_risk >= RR_GOOD:
        out.append(
            Check(
                "reward_risk",
                "configuration",
                Severity.GOOD,
                f"Reward to risk is {reward_risk:.1f}:1",
                detail,
            )
        )
    else:
        out.append(
            Check(
                "reward_risk",
                "configuration",
                Severity.INFO,
                f"Reward to risk is {reward_risk:.1f}:1",
                detail,
                "1.5:1 or better gives more room for a low win rate.",
            )
        )
    if target < 2 * ROUND_TRIP_COST:
        out.append(
            Check(
                "target_vs_costs",
                "configuration",
                Severity.WARN,
                f"Target ({_pct(target)}) is close to trading costs",
                f"A round trip costs roughly {_pct(ROUND_TRIP_COST)} in brokerage, taxes and fees, plus slippage. Small targets are mostly eaten by costs.",
                "Use a larger target or a slower timeframe.",
            )
        )
    return out


def _timeframe(inp: ReviewInput) -> Check:
    tf = inp.timeframe
    if tf is Timeframe.M1:
        return Check(
            "timeframe",
            "configuration",
            Severity.WARN,
            "1-minute timeframe: costs dominate",
            "Every round trip pays brokerage, taxes and slippage, and a 1-minute strategy trades very often, so costs compound quickly.",
            "Prefer 5 minutes or slower unless a backtest with costs shows a clear edge.",
        )
    if tf is Timeframe.M5:
        return Check(
            "timeframe",
            "configuration",
            Severity.INFO,
            "5-minute timeframe",
            "Trades often enough that costs matter. Check the backtest's total charges.",
        )
    return Check(
        "timeframe",
        "configuration",
        Severity.GOOD,
        f"Timeframe {tf.value}",
        "A slower timeframe trades less often, so costs weigh less.",
    )


def _parameters(inp: ReviewInput) -> list[Check]:
    p, out = inp.parameters, []
    if inp.strategy_type is StrategyType.EMA_CROSSOVER:
        fast, slow = p.get("fast_period", 20), p.get("slow_period", 50)
        if slow < 20:
            out.append(
                Check(
                    "ema_periods",
                    "configuration",
                    Severity.WARN,
                    f"Slow EMA is short ({slow})",
                    "Very short averages cross back and forth in sideways markets, which produces many losing whipsaw trades.",
                    "Try a slow period of 30 or more.",
                )
            )
        elif fast / slow > 0.7:
            out.append(
                Check(
                    "ema_periods",
                    "configuration",
                    Severity.WARN,
                    "Fast and slow EMAs are close together",
                    "Lines this close cross constantly and give noisy signals.",
                    "Keep the fast period well below the slow one, for example 20 and 50.",
                )
            )
        else:
            out.append(
                Check(
                    "ema_periods",
                    "configuration",
                    Severity.GOOD,
                    f"EMA periods {fast}/{slow}",
                    "The two averages are far enough apart to filter some noise.",
                )
            )
    elif inp.strategy_type is StrategyType.BREAKOUT:
        lookback = p.get("lookback_period", 20)
        if lookback < 10:
            out.append(
                Check(
                    "lookback",
                    "configuration",
                    Severity.WARN,
                    f"Breakout lookback is short ({lookback})",
                    "A short channel is broken by ordinary moves, so many breakouts fail.",
                    "Try a lookback of 20 bars or more.",
                )
            )
        else:
            out.append(
                Check(
                    "lookback",
                    "configuration",
                    Severity.GOOD,
                    f"Breakout lookback {lookback} bars",
                    "The channel is long enough to represent a real range.",
                )
            )
    elif inp.strategy_type is StrategyType.VWAP and p.get("band_pct", 0) == 0 and p.get("window", 0) == 0:
        out.append(
            Check(
                "vwap_band",
                "configuration",
                Severity.INFO,
                "No confirmation band around VWAP",
                "Without a band, small wiggles around VWAP trigger trades.",
                "A band of 0.05% to 0.2% removes many false crosses.",
            )
        )
    return out


def _mode_and_account(inp: ReviewInput, paper: PaperRecord | None) -> list[Check]:
    out: list[Check] = []
    if inp.config_error:
        out.append(
            Check(
                "config_valid",
                "configuration",
                Severity.RISK,
                "Strategy parameters are invalid",
                inp.config_error,
            )
        )
    if inp.trading_mode is TradingMode.PAPER:
        out.append(
            Check(
                "mode",
                "safety",
                Severity.GOOD,
                "Paper mode: no real money at risk",
                "Orders go to the simulated broker. This is the right place to learn and test.",
            )
        )
    elif inp.trading_mode is TradingMode.SANDBOX:
        out.append(
            Check(
                "mode",
                "safety",
                Severity.INFO,
                "Sandbox mode",
                "Orders go to the broker's test environment. No real money, but the broker's rules apply.",
            )
        )
    else:
        out.append(
            Check(
                "mode",
                "safety",
                Severity.RISK,
                "Live mode uses real money",
                "Losses are real. Live trading also needs every safety switch enabled by an administrator.",
                "Run in paper mode for several weeks first.",
            )
        )
    if inp.trading_mode is not TradingMode.PAPER:
        trades = paper.trades if paper else 0
        if trades < MIN_PAPER_TRADES_BEFORE_REAL_MONEY:
            out.append(
                Check(
                    "paper_record",
                    "safety",
                    Severity.RISK,
                    "Not enough paper trading history",
                    f"Only {trades} paper trades recorded; at least {MIN_PAPER_TRADES_BEFORE_REAL_MONEY} are recommended before risking real money.",
                    "Run this strategy in paper mode until it has a real track record.",
                )
            )
        elif paper and paper.net_pnl <= 0:
            out.append(
                Check(
                    "paper_record",
                    "safety",
                    Severity.WARN,
                    "Paper trading was not profitable",
                    f"{paper.trades} paper trades netted ₹{paper.net_pnl:,.2f} after costs.",
                )
            )
        else:
            out.append(
                Check(
                    "paper_record",
                    "safety",
                    Severity.GOOD,
                    "Positive paper track record",
                    f"{paper.trades if paper else 0} paper trades, profitable after costs.",
                )
            )
    elif paper and paper.trades > 0:
        sev = Severity.GOOD if paper.net_pnl > 0 else Severity.INFO
        out.append(
            Check(
                "paper_record",
                "safety",
                sev,
                f"Paper record: {paper.trades} trades",
                f"Net result after costs is ₹{paper.net_pnl:,.2f}. Small samples say little; judge it after {MIN_PAPER_TRADES_BEFORE_REAL_MONEY}+ trades.",
            )
        )
    if inp.allow_short:
        out.append(
            Check(
                "short",
                "safety",
                Severity.INFO,
                "Short selling is enabled",
                "Equity shorts are intraday only: the position must be closed before the market closes, and this platform does not auto square-off yet. Losses on a short are unlimited in theory, so the stop matters.",
                "Keep the stop loss on, and stop the strategy before the close.",
            )
        )
    if inp.account_capital is not None and inp.capital > inp.account_capital + 1e-6:
        out.append(
            Check(
                "capital",
                "configuration",
                Severity.WARN,
                "Strategy capital is more than the account holds",
                f"Strategy capital ₹{inp.capital:,.0f} exceeds account capital ₹{inp.account_capital:,.0f}, so larger orders will be rejected for lack of funds.",
                "Lower the strategy capital.",
            )
        )
    return out


# ---- backtest evidence -----------------------------------------------------------------------------
def _backtest(inp: ReviewInput, evidence: BacktestEvidence | None) -> list[Check]:
    if evidence is None:
        sev = Severity.WARN if inp.trading_mode is TradingMode.PAPER else Severity.RISK
        return [
            Check(
                "backtest_missing",
                "backtest",
                sev,
                "Not backtested yet",
                "There is no completed backtest for this strategy, so nothing shows how it behaves with costs.",
                "Save the strategy and run a backtest over at least 3 months.",
            )
        ]
    out: list[Check] = []
    if evidence.stale:
        out.append(
            Check(
                "backtest_stale",
                "backtest",
                Severity.WARN,
                "Backtest is out of date",
                "The strategy settings changed after this backtest ran, so the results below describe an older version.",
                "Run the backtest again.",
            )
        )
    if evidence.data_source == "simulated":
        out.append(
            Check(
                "backtest_synthetic",
                "backtest",
                Severity.WARN,
                "Backtest used synthetic data",
                "Simulated prices are generated by the platform. Results say nothing about how the strategy would behave in real markets.",
                "Connect a real market data provider before trusting any backtest.",
            )
        )
    if evidence.period_days < MIN_BACKTEST_DAYS:
        out.append(
            Check(
                "backtest_period",
                "backtest",
                Severity.WARN,
                f"Backtest covers only {evidence.period_days} days",
                "A short window captures a single market mood.",
                f"Test at least {GOOD_BACKTEST_DAYS} days.",
            )
        )
    elif evidence.period_days < GOOD_BACKTEST_DAYS:
        out.append(
            Check(
                "backtest_period",
                "backtest",
                Severity.INFO,
                f"Backtest covers {evidence.period_days} days",
                f"{GOOD_BACKTEST_DAYS}+ days, including both rising and falling markets, is better.",
            )
        )
    else:
        out.append(
            Check(
                "backtest_period",
                "backtest",
                Severity.GOOD,
                f"Backtest covers {evidence.period_days} days",
                "A reasonably long window.",
            )
        )

    if evidence.trades < MIN_TRADES_MEANINGFUL:
        out.append(
            Check(
                "backtest_sample",
                "backtest",
                Severity.WARN,
                f"Only {evidence.trades} trades in the backtest",
                "Too few trades to tell skill from luck.",
                f"Aim for {MIN_TRADES_MEANINGFUL}+ trades, ideally {MIN_TRADES_GOOD}+.",
            )
        )
    elif evidence.trades < MIN_TRADES_GOOD:
        out.append(
            Check(
                "backtest_sample",
                "backtest",
                Severity.INFO,
                f"{evidence.trades} trades in the backtest",
                f"Usable, but {MIN_TRADES_GOOD}+ trades give a firmer picture.",
            )
        )
    else:
        out.append(
            Check(
                "backtest_sample",
                "backtest",
                Severity.GOOD,
                f"{evidence.trades} trades in the backtest",
                "A decent sample size.",
            )
        )

    if evidence.net_pnl <= 0:
        out.append(
            Check(
                "backtest_profit",
                "backtest",
                Severity.RISK,
                "Backtest lost money after costs",
                f"Net result ₹{evidence.net_pnl:,.2f} including brokerage, taxes and slippage. A strategy that loses in a backtest is unlikely to win live.",
                "Change the parameters or the timeframe, or pick another strategy.",
            )
        )
    elif evidence.profit_factor is None:
        out.append(
            Check(
                "backtest_profit",
                "backtest",
                Severity.INFO,
                "Profitable with no losing trades",
                "Almost certainly too few trades to trust.",
            )
        )
    elif evidence.profit_factor >= PROFIT_FACTOR_GOOD:
        out.append(
            Check(
                "backtest_profit",
                "backtest",
                Severity.GOOD,
                f"Profit factor {evidence.profit_factor:.2f}",
                "Winning trades earned clearly more than losing trades lost, after costs.",
            )
        )
    else:
        out.append(
            Check(
                "backtest_profit",
                "backtest",
                Severity.WARN,
                f"Profit factor is thin ({evidence.profit_factor:.2f})",
                "The edge is small and could disappear with slightly worse fills.",
                f"Look for {PROFIT_FACTOR_GOOD} or better.",
            )
        )

    if evidence.max_drawdown_pct >= DRAWDOWN_RISK_PCT:
        out.append(
            Check(
                "backtest_drawdown",
                "backtest",
                Severity.RISK,
                f"Maximum drawdown {evidence.max_drawdown_pct:.1f}%",
                "The account fell by a fifth or more from its peak. Few people can hold a strategy through that.",
                "Lower the risk per trade or tighten the strategy.",
            )
        )
    elif evidence.max_drawdown_pct >= DRAWDOWN_WARN_PCT:
        out.append(
            Check(
                "backtest_drawdown",
                "backtest",
                Severity.WARN,
                f"Maximum drawdown {evidence.max_drawdown_pct:.1f}%",
                "Expect deeper losing periods live than in the backtest.",
                "Consider a smaller risk per trade.",
            )
        )
    else:
        out.append(
            Check(
                "backtest_drawdown",
                "backtest",
                Severity.GOOD,
                f"Maximum drawdown {evidence.max_drawdown_pct:.1f}%",
                "The worst peak-to-trough loss was moderate.",
            )
        )

    if evidence.gross_profit > 0 and evidence.total_charges > COST_SHARE_WARN * evidence.gross_profit:
        share = evidence.total_charges / evidence.gross_profit
        out.append(
            Check(
                "backtest_costs",
                "backtest",
                Severity.WARN,
                "Costs take a large share of profits",
                f"Total charges of ₹{evidence.total_charges:,.0f} equal {share:.0%} of gross profit, so small changes in costs flip the result.",
                "Trade less often (slower timeframe) or use larger targets.",
            )
        )
    return out


def review_strategy(
    inp: ReviewInput, evidence: BacktestEvidence | None = None, paper: PaperRecord | None = None
) -> Review:
    checks: list[Check] = []
    checks += _mode_and_account(inp, paper)
    checks += _risk_per_trade(inp)
    checks += _stop_and_target(inp)
    checks.append(_timeframe(inp))
    checks += _parameters(inp)
    checks += _backtest(inp, evidence)

    order = {Severity.RISK: 0, Severity.WARN: 1, Severity.INFO: 2, Severity.GOOD: 3}
    checks.sort(key=lambda c: order[c.severity])
    risks = sum(1 for c in checks if c.severity is Severity.RISK)
    warns = sum(1 for c in checks if c.severity is Severity.WARN)

    if risks:
        verdict = Verdict.NOT_RECOMMENDED
        summary = f"Not recommended to run yet: {risks} serious {'issue' if risks == 1 else 'issues'}" + (
            f" and {warns} warning{'s' if warns != 1 else ''}." if warns else "."
        )
    elif warns:
        verdict = Verdict.CAUTION
        summary = f"Usable, with {warns} thing{'s' if warns != 1 else ''} worth fixing first."
    else:
        verdict = Verdict.RECOMMENDED
        summary = "Follows the common good-practice guidelines."
    if inp.trading_mode is TradingMode.PAPER and verdict is not Verdict.RECOMMENDED:
        summary += " Paper trading is a safe place to experiment, so starting is still allowed."
    return Review(verdict, summary, tuple(checks))


def config_matches(
    backtest_config: dict[str, Any],
    backtest_params: dict[str, Any],
    inp: ReviewInput,
    symbol_matches: bool,
    timeframe_matches: bool,
) -> bool:
    """True when a stored backtest was run with the strategy's current settings."""

    def same(a: Any, b: Any) -> bool:
        if a is None or b is None:
            return a is b
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)

    return (
        symbol_matches
        and timeframe_matches
        and {k: float(v) for k, v in backtest_params.items()}
        == {k: float(v) for k, v in inp.parameters.items()}
        and same(backtest_config.get("risk_per_trade"), inp.risk_per_trade)
        and same(backtest_config.get("stop_loss_pct"), inp.stop_loss_pct)
        and same(backtest_config.get("target_pct"), inp.target_pct)
        and bool(backtest_config.get("allow_short")) == inp.allow_short
    )
