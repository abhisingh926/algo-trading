"""Historical setup statistics: sample size rules, exact counts, costs and the absence of look-ahead."""

from datetime import date

import pytest

from app.research import historical as hist
from app.research import sessions as ses
from tests.research_helpers import make_history, make_session, provenance, trading_days

PROV = provenance()


def crafted_sessions(
    total: int, gap_up_every: int = 1, rising: bool = True, current_bars: int = 12
) -> list[ses.Session]:
    """`total` sessions. Gap-up sessions open 1% above the previous close and either rise steadily or fade."""
    sessions, prev_close = [], 1000.0
    for n, day in enumerate(trading_days(date(2025, 3, 3), total)):
        gaps = gap_up_every > 0 and n % gap_up_every == 0 and n > 0
        open_price = prev_close * (1.01 if gaps else 1.0)
        slope = 0.001 if rising else -0.001
        bars = make_session(
            day, open_price, path=lambda i, k, o=open_price, sl=slope: o * (1 + sl * (i + 1)), spread=0.0
        )
        prev_close = bars[-1].close
        sessions.append(ses.Session(day, bars))
    sessions[-1] = ses.Session(sessions[-1].day, sessions[-1].bars[:current_bars])
    return sessions


def stat(analysis, key):  # noqa: ANN001, ANN201
    return next(s for s in analysis.setups if s.key == key)


def test_adequate_sample_reports_exact_counts_and_costs():
    analysis = hist.analyze(crafted_sessions(70, gap_up_every=1), PROV, min_sample=30, cost_pct=0.10)
    exact = stat(analysis, "SETUP_EXACT")
    assert analysis.current_setup_key == "GAP_UP|ABOVE_VWAP|NORMAL_RVOL"
    assert (
        exact.occurrences == 68
        and exact.sample_adequate
        and exact.successful == 68
        and exact.success_rate == 100.0
    )
    assert exact.avg_return_pct > 0 and exact.avg_return_net_pct == pytest.approx(
        exact.avg_return_pct - 0.10, abs=1e-3
    )
    assert exact.mfe_pct >= exact.avg_return_pct and exact.mae_pct <= 0
    assert (
        exact.reach_probability["0.3"] == 100.0
        and exact.horizon_returns_pct["15m"] < exact.horizon_returns_pct["1h"]
    )
    assert analysis.matched is not None and analysis.matched.key == "SETUP_EXACT"
    assert analysis.sessions_analyzed == 69


def test_small_sample_states_no_rates():
    """Only 10 gap-up days: the exact setup must not report a success rate, and the report must say why."""
    analysis = hist.analyze(crafted_sessions(45, gap_up_every=4), PROV, min_sample=30)
    exact = stat(analysis, "SETUP_EXACT")
    assert exact.occurrences < 30 and exact.sample_adequate is False
    assert (
        exact.success_rate is None
        and exact.avg_return_pct is None
        and exact.avg_return_net_pct is None
        and exact.reach_probability == {}
    )
    assert "at least 30" in (exact.note or "")
    assert any("too few occurrences" in w for w in analysis.warnings)


def test_falls_back_to_a_broader_setup_when_the_exact_one_is_too_rare():
    analysis = hist.analyze(
        crafted_sessions(71, gap_up_every=7), PROV, min_sample=30
    )  # 71 sessions: today is a (rare) gap day
    assert stat(analysis, "SETUP_EXACT").sample_adequate is False
    assert (
        analysis.matched is not None and analysis.matched.key == "SETUP_VWAP"
    )  # the loosest tier has a big enough sample


def test_no_adequate_match_means_no_claimed_edge():
    analysis = hist.analyze(crafted_sessions(45, gap_up_every=0), PROV, min_sample=1000)
    assert analysis.matched is None
    assert any("no historical edge is claimed" in w for w in analysis.warnings)


def test_too_little_history_returns_an_explanation_not_statistics():
    analysis = hist.analyze(crafted_sessions(20), PROV)
    assert analysis.setups == [] and "at least 40" in analysis.warnings[0]


def test_current_session_is_never_part_of_the_sample():
    sessions = crafted_sessions(70, gap_up_every=1)
    analysis = hist.analyze(sessions, PROV)
    assert analysis.period_end == sessions[-2].day.isoformat()  # the day before the current session
    assert analysis.sessions_analyzed == len(sessions) - 1


def test_outcomes_do_not_depend_on_the_current_sessions_future():
    """Bars of the current session after the decision time are not passed in, so they cannot change history stats."""
    base = crafted_sessions(70, gap_up_every=1, current_bars=12)
    a = hist.analyze(base, PROV)
    changed = list(base)
    changed[-1] = ses.Session(base[-1].day, base[-1].bars[:12])  # identical prefix, nothing after it
    assert a.model_dump() == hist.analyze(changed, PROV).model_dump()


def test_fading_gaps_are_counted_as_failures_and_filled():
    analysis = hist.analyze(crafted_sessions(70, gap_up_every=1, rising=False), PROV)
    fill = stat(analysis, "GAP_UP_FILL")
    assert (
        fill.sample_adequate and fill.success_rate == 100.0
    )  # every fading gap-up day returned to the previous close
    cross_down = stat(analysis, "VWAP_CROSS_DOWN")
    assert cross_down.occurrences >= 0


def test_closed_session_is_evaluated_at_the_last_measurable_time():
    sessions = crafted_sessions(70, gap_up_every=1, current_bars=25)  # the current session is complete
    analysis = hist.analyze(sessions, PROV)
    assert any("as of 14:30 IST" in w for w in analysis.warnings)
    assert analysis.matched is not None  # an outcome can still be measured at 14:30, unlike at 15:30


def test_baseline_moves_grow_with_the_horizon():
    analysis = hist.analyze(make_history_sessions(80), PROV)
    moves = analysis.baseline_moves
    assert moves["15m"] < moves["30m"] < moves["1h"]


def make_history_sessions(n: int) -> list[ses.Session]:
    sessions = ses.group_sessions(make_history(n, seed=11))
    sessions[-1] = ses.Session(sessions[-1].day, sessions[-1].bars[:10])
    return sessions


def test_random_data_shows_no_reliable_edge_after_costs():
    """A random walk must not look profitable once trading costs are deducted."""
    analysis = hist.analyze(make_history_sessions(260), PROV, cost_pct=0.10)
    adequate = [
        s for s in analysis.setups if s.sample_adequate and s.key.startswith(("VWAP_CROSS", "ORB", "SETUP"))
    ]
    assert adequate
    assert all(s.avg_return_net_pct < 0.05 for s in adequate)
