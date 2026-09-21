"""Good-practice review (pure logic) + the guide endpoints."""

from datetime import timedelta

import pytest

from app.domain.enums import StrategyType, Timeframe, TradingMode
from app.risk.strategy_review import (
    BacktestEvidence,
    PaperRecord,
    ReviewInput,
    Severity,
    Verdict,
    review_strategy,
)
from app.utils.time import ist_today
from tests.conftest import make_candles


def setup(**overrides) -> ReviewInput:
    base = dict(
        strategy_type=StrategyType.EMA_CROSSOVER,
        timeframe=Timeframe.M15,
        capital=100_000,
        risk_per_trade=0.01,
        stop_loss_pct=0.01,
        target_pct=0.02,
        allow_short=False,
        trading_mode=TradingMode.PAPER,
        parameters={"fast_period": 20, "slow_period": 50},
        account_capital=500_000,
        platform_max_risk_per_trade=0.01,
    )
    return ReviewInput(**(base | overrides))


def evidence(**overrides) -> BacktestEvidence:
    base = dict(
        trades=150,
        net_pnl=12_000,
        profit_factor=1.6,
        max_drawdown_pct=6.0,
        gross_profit=30_000,
        total_charges=5_000,
        data_source="dhan",
        period_days=180,
        sharpe_ratio=1.1,
        stale=False,
    )
    return BacktestEvidence(**(base | overrides))


def severities(review) -> dict[str, Severity]:
    return {c.key: c.severity for c in review.checks}


class TestConfiguration:
    def test_sensible_setup_with_real_data_backtest_is_recommended(self):
        review = review_strategy(setup(), evidence())
        assert (
            review.verdict is Verdict.RECOMMENDED
            and review.count(Severity.WARN) == 0
            and review.count(Severity.RISK) == 0
        )

    @pytest.mark.parametrize(
        "risk, expected",
        [
            (0.005, Severity.GOOD),
            (0.01, Severity.GOOD),
            (0.02, Severity.INFO),
            (0.03, Severity.WARN),
            (0.06, Severity.RISK),
        ],
    )
    def test_risk_per_trade_bands(self, risk, expected):
        assert (
            severities(review_strategy(setup(risk_per_trade=risk), evidence()))["risk_per_trade"] is expected
        )

    def test_risk_detail_explains_a_losing_streak(self):
        check = next(
            c
            for c in review_strategy(setup(risk_per_trade=0.02), evidence()).checks
            if c.key == "risk_per_trade"
        )
        assert "18%" in check.detail  # 1 - 0.98**10

    def test_stop_loss_bands(self):
        assert (
            severities(review_strategy(setup(stop_loss_pct=0.001, target_pct=0.004), evidence()))["stop_loss"]
            is Severity.WARN
        )
        assert (
            severities(review_strategy(setup(stop_loss_pct=0.08, target_pct=0.2), evidence()))["stop_loss"]
            is Severity.WARN
        )
        assert severities(review_strategy(setup(), evidence()))["stop_loss"] is Severity.GOOD

    def test_target_checks(self):
        assert severities(review_strategy(setup(target_pct=None), evidence()))["target"] is Severity.WARN
        assert (
            severities(review_strategy(setup(target_pct=0.005), evidence()))["reward_risk"] is Severity.WARN
        )
        assert (
            severities(review_strategy(setup(target_pct=0.015), evidence()))["reward_risk"] is Severity.GOOD
        )
        tiny = review_strategy(setup(stop_loss_pct=0.002, target_pct=0.0015), evidence())
        assert severities(tiny)["target_vs_costs"] is Severity.WARN

    def test_break_even_win_rate_is_explained(self):
        check = next(
            c for c in review_strategy(setup(target_pct=0.02), evidence()).checks if c.key == "reward_risk"
        )
        assert "33%" in check.detail  # 1 / (1 + 2)

    def test_timeframe_bands(self):
        assert (
            severities(review_strategy(setup(timeframe=Timeframe.M1), evidence()))["timeframe"]
            is Severity.WARN
        )
        assert (
            severities(review_strategy(setup(timeframe=Timeframe.M5), evidence()))["timeframe"]
            is Severity.INFO
        )
        assert (
            severities(review_strategy(setup(timeframe=Timeframe.H1), evidence()))["timeframe"]
            is Severity.GOOD
        )

    def test_ema_parameter_advice(self):
        short = review_strategy(setup(parameters={"fast_period": 3, "slow_period": 8}), evidence())
        assert severities(short)["ema_periods"] is Severity.WARN
        close = review_strategy(setup(parameters={"fast_period": 40, "slow_period": 50}), evidence())
        assert severities(close)["ema_periods"] is Severity.WARN

    def test_breakout_and_vwap_advice(self):
        short = review_strategy(
            setup(strategy_type=StrategyType.BREAKOUT, parameters={"lookback_period": 5}), evidence()
        )
        assert severities(short)["lookback"] is Severity.WARN
        vwap = review_strategy(
            setup(strategy_type=StrategyType.VWAP, parameters={"band_pct": 0, "window": 0, "min_bars": 5}),
            evidence(),
        )
        assert severities(vwap)["vwap_band"] is Severity.INFO

    def test_platform_cap_and_account_capital(self):
        review = review_strategy(
            setup(risk_per_trade=0.02, platform_max_risk_per_trade=0.01, capital=900_000), evidence()
        )
        assert "risk_platform_cap" in severities(review) and severities(review)["capital"] is Severity.WARN

    def test_invalid_parameters_are_reported_as_a_serious_issue(self):
        review = review_strategy(
            setup(config_error="fast_period must be smaller than slow_period"), evidence()
        )
        assert (
            severities(review)["config_valid"] is Severity.RISK and review.verdict is Verdict.NOT_RECOMMENDED
        )

    def test_short_selling_is_flagged(self):
        check = next(
            c for c in review_strategy(setup(allow_short=True), evidence()).checks if c.key == "short"
        )
        assert "intraday" in check.detail and "square-off" in check.detail


class TestBacktestEvidence:
    def test_missing_backtest_is_a_warning_in_paper_and_serious_otherwise(self):
        assert severities(review_strategy(setup(), None))["backtest_missing"] is Severity.WARN
        assert (
            severities(review_strategy(setup(trading_mode=TradingMode.SANDBOX), None))["backtest_missing"]
            is Severity.RISK
        )

    def test_losing_backtest_is_not_recommended(self):
        review = review_strategy(setup(), evidence(net_pnl=-5_000, profit_factor=0.8))
        assert (
            severities(review)["backtest_profit"] is Severity.RISK
            and review.verdict is Verdict.NOT_RECOMMENDED
        )
        assert "Paper trading is a safe place" in review.summary

    def test_profit_factor_bands(self):
        assert (
            severities(review_strategy(setup(), evidence(profit_factor=1.1)))["backtest_profit"]
            is Severity.WARN
        )
        assert (
            severities(review_strategy(setup(), evidence(profit_factor=1.5)))["backtest_profit"]
            is Severity.GOOD
        )

    def test_drawdown_bands(self):
        assert (
            severities(review_strategy(setup(), evidence(max_drawdown_pct=12)))["backtest_drawdown"]
            is Severity.WARN
        )
        assert (
            severities(review_strategy(setup(), evidence(max_drawdown_pct=25)))["backtest_drawdown"]
            is Severity.RISK
        )

    def test_sample_size_and_period(self):
        assert severities(review_strategy(setup(), evidence(trades=12)))["backtest_sample"] is Severity.WARN
        assert severities(review_strategy(setup(), evidence(trades=60)))["backtest_sample"] is Severity.INFO
        assert (
            severities(review_strategy(setup(), evidence(period_days=10)))["backtest_period"] is Severity.WARN
        )

    def test_synthetic_stale_and_costs(self):
        review = review_strategy(setup(), evidence(data_source="simulated", stale=True, total_charges=20_000))
        keys = severities(review)
        assert keys["backtest_synthetic"] is Severity.WARN and keys["backtest_stale"] is Severity.WARN
        assert keys["backtest_costs"] is Severity.WARN

    def test_checks_are_sorted_worst_first_and_verdict_matches(self):
        review = review_strategy(setup(risk_per_trade=0.06), evidence(data_source="simulated"))
        order = [c.severity for c in review.checks]
        assert order == sorted(order, key=["RISK", "WARN", "INFO", "GOOD"].index)
        assert review.verdict is Verdict.NOT_RECOMMENDED


class TestRealMoneyGuardrails:
    def test_live_needs_a_paper_track_record(self):
        review = review_strategy(
            setup(trading_mode=TradingMode.LIVE), evidence(), PaperRecord(trades=5, net_pnl=100)
        )
        assert (
            severities(review)["mode"] is Severity.RISK
            and severities(review)["paper_record"] is Severity.RISK
        )
        good = review_strategy(
            setup(trading_mode=TradingMode.LIVE), evidence(), PaperRecord(trades=80, net_pnl=4_000)
        )
        assert severities(good)["paper_record"] is Severity.GOOD
        losing = review_strategy(
            setup(trading_mode=TradingMode.LIVE), evidence(), PaperRecord(trades=80, net_pnl=-4_000)
        )
        assert severities(losing)["paper_record"] is Severity.WARN

    def test_paper_mode_shows_a_record_when_there_is_one(self):
        review = review_strategy(setup(), evidence(), PaperRecord(trades=8, net_pnl=-200))
        assert severities(review)["paper_record"] is Severity.INFO


DRAFT = {
    "strategy_type": "EMA_CROSSOVER",
    "symbol": "RELIANCE",
    "timeframe": "15m",
    "capital": 100000,
    "risk_per_trade": 0.01,
    "stop_loss_pct": 0.01,
    "target_pct": 0.02,
    "parameters": {"fast_period": 20, "slow_period": 50},
}


async def test_draft_review_endpoint(client):
    response = await client.post("/api/v1/strategies/review", json=DRAFT)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["has_backtest"] is False and data["verdict"] == "CAUTION"
    assert {c["key"] for c in data["checks"]} >= {"risk_per_trade", "stop_loss", "backtest_missing"}
    assert set(data["counts"]) == {"good", "info", "warn", "risk"} and data["disclaimer"]

    invalid = await client.post(
        "/api/v1/strategies/review", json=DRAFT | {"parameters": {"fast_period": 60, "slow_period": 50}}
    )
    assert invalid.status_code == 200 and invalid.json()["data"]["verdict"] == "NOT_RECOMMENDED"
    assert (
        await client.post("/api/v1/strategies/review", json=DRAFT | {"risk_per_trade": 5})
    ).status_code == 422


async def test_saved_strategy_review_uses_its_backtest_and_detects_staleness(client, market_data):
    from datetime import UTC, datetime, time

    strategy = (
        await client.post(
            "/api/v1/strategies",
            json=DRAFT
            | {"name": "Review me", "timeframe": "5m", "parameters": {"fast_period": 5, "slow_period": 12}},
        )
    ).json()["data"]
    assert (await client.get(f"/api/v1/strategies/{strategy['id']}/review")).json()["data"][
        "has_backtest"
    ] is False

    start_day = ist_today() - timedelta(days=5)
    closes = [100 + (i % 40) * 0.5 if (i // 40) % 2 == 0 else 120 - (i % 40) * 0.5 for i in range(400)]
    market_data.candles["RELIANCE"] = make_candles(
        closes, start=datetime.combine(start_day, time(4, 0), tzinfo=UTC)
    )
    run = await client.post(
        "/api/v1/backtests",
        json={
            "strategy_id": strategy["id"],
            "start_date": str(start_day),
            "end_date": str(ist_today()),
            "initial_capital": 100000,
        },
    )
    assert run.json()["data"]["status"] == "COMPLETED"

    review = (await client.get(f"/api/v1/strategies/{strategy['id']}/review")).json()["data"]
    keys = {c["key"]: c["severity"] for c in review["checks"]}
    assert review["has_backtest"] and review["backtest_id"] == run.json()["data"]["id"]
    assert "backtest_missing" not in keys and "backtest_stale" not in keys
    assert keys["backtest_period"] == "WARN"  # only a few days of data

    await client.put(
        f"/api/v1/strategies/{strategy['id']}", json={"parameters": {"fast_period": 8, "slow_period": 21}}
    )
    stale = (await client.get(f"/api/v1/strategies/{strategy['id']}/review")).json()["data"]
    assert {c["key"]: c["severity"] for c in stale["checks"]}["backtest_stale"] == "WARN"

    assert (await client.get("/api/v1/strategies/nope/review")).status_code == 404


async def test_onboarding_checklist_tracks_real_progress(client, market_data):
    from datetime import UTC, datetime, time

    def by_key(steps):
        return {s["key"]: s["done"] for s in steps}

    first = (await client.get("/api/v1/guide/onboarding")).json()["data"]
    assert (
        first["percent"] == 14
        and first["total"] == 7
        and first["completed"] == 1
        and first["next_step"] == "review_risk"
    )
    assert by_key(first["steps"]) == {
        "paper_mode": True,
        "review_risk": False,
        "create_strategy": False,
        "run_backtest": False,
        "start_strategy": False,
        "first_order": False,
        "first_trade": False,
        "test_kill_switch": False,
    }
    assert [s["key"] for s in first["steps"] if s["optional"]] == ["test_kill_switch"]

    await client.put("/api/v1/risk", json={"max_daily_loss": 4000})
    strategy = (
        await client.post(
            "/api/v1/strategies",
            json=DRAFT
            | {"name": "Guide flow", "timeframe": "5m", "parameters": {"fast_period": 5, "slow_period": 12}},
        )
    ).json()["data"]
    start_day = ist_today() - timedelta(days=5)
    market_data.candles["RELIANCE"] = make_candles(
        [100 + (i % 40) * 0.5 for i in range(400)], start=datetime.combine(start_day, time(4, 0), tzinfo=UTC)
    )
    await client.post(
        "/api/v1/backtests",
        json={
            "strategy_id": strategy["id"],
            "start_date": str(start_day),
            "end_date": str(ist_today()),
            "initial_capital": 100000,
        },
    )
    await client.post(f"/api/v1/strategies/{strategy['id']}/start")
    await client.post("/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 5})
    mid = (await client.get("/api/v1/guide/onboarding")).json()["data"]
    assert (
        by_key(mid["steps"])["review_risk"]
        and by_key(mid["steps"])["create_strategy"]
        and by_key(mid["steps"])["run_backtest"]
    )
    assert (
        by_key(mid["steps"])["start_strategy"]
        and by_key(mid["steps"])["first_order"]
        and not by_key(mid["steps"])["first_trade"]
    )
    assert mid["next_step"] == "first_trade" and not mid["all_done"]

    await client.post("/api/v1/orders", json={"symbol": "RELIANCE", "side": "SELL", "quantity": 5})
    done = (await client.get("/api/v1/guide/onboarding")).json()["data"]
    assert (
        done["all_done"]
        and done["percent"] == 100
        and done["next_step"] is None
        and by_key(done["steps"])["test_kill_switch"] is False
    )
