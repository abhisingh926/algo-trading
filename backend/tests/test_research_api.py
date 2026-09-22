"""End-to-end research: real orchestrator, real services and database (SQLite), simulated market data over HTTP."""

import csv
import io
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio

from app.domain.enums import Timeframe
from app.domain.types import Candle
from app.main import create_app
from app.market_data.simulated import SimulatedMarketDataProvider
from app.models.research import ResearchRun
from app.services.factory import Services
from app.trading.engine import TradingEngine
from app.utils.time import utcnow
from tests.conftest import build_container, make_settings

SYMBOLS = ["RELIANCE", "TCS", "INFY"]


@pytest_asyncio.fixture
async def research():  # noqa: ANN201
    settings = make_settings(research_history_days=100, log_level="ERROR")
    container = await build_container(settings, SimulatedMarketDataProvider(always_open=True))
    app = create_app(settings, container)
    app.state.container = container
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield container, client
    await container.close()


async def start(client, container, depth="STANDARD", symbols=None, as_of=None):  # noqa: ANN001, ANN201
    body = {"universe": "CUSTOM", "symbols": symbols or SYMBOLS, "depth": depth}
    if as_of:
        body["as_of"] = as_of.isoformat()
    response = await client.post("/api/v1/research/run", json=body)
    assert response.status_code == 201, response.text
    run = response.json()["data"]
    await container.research_runner.wait(run["id"])
    return run["id"]


async def test_full_research_flow(research):
    container, client = research

    # ---- first run (Quick depth, two days ago) -------------------------------------------------
    started = await client.post(
        "/api/v1/research/run",
        json={
            "universe": "CUSTOM",
            "symbols": SYMBOLS,
            "depth": "QUICK",
            "as_of": (utcnow() - timedelta(days=2)).isoformat(),
        },
    )
    assert started.status_code == 201 and started.json()["data"]["status"] == "PENDING"
    run_id = started.json()["data"]["id"]
    blocked = await client.post("/api/v1/research/run", json={"universe": "CUSTOM", "symbols": ["TCS"]})
    assert blocked.status_code == 409 and "still in progress" in blocked.json()["status"]["description"]
    await container.research_runner.wait(run_id)

    run = (await client.get(f"/api/v1/research/runs/{run_id}")).json()["data"]
    assert (
        run["status"] == "COMPLETED"
        and run["candidates_analyzed"] == 3
        and run["is_synthetic"] is True
        and run["data_source"] == "simulated"
    )
    agents = {a["agent"]: a for a in run["agents"]}
    assert len(agents) == 9
    assert agents["MarketScannerAgent"]["status"] == "SUCCESS" and agents["QuantScoringAgent"]["records"] == 3
    for name in ("MarketResearchAgent", "NewsCatalystAgent", "FundamentalResearchAgent"):
        assert agents[name]["status"] == "NOT_AVAILABLE" and agents[name]["message"]
    assert agents["DataVerificationAgent"]["status"] == "SKIPPED"  # Quick depth skips verification

    # ---- candidates: ranking, filters, sorting --------------------------------------------------
    listing = (await client.get("/api/v1/research/candidates")).json()["data"]
    items = listing["items"]
    assert [i["rank"] for i in items] == [1, 2, 3] and listing["run"]["id"] == run_id
    scores = [i["research_score"] for i in items]
    assert scores == sorted(scores, reverse=True) and all(0 <= s <= 100 for s in scores)
    assert all(i["data_confidence"] <= 30 for i in items) and all(
        i["catalyst"] == "Not assessed" for i in items
    )
    top = items[0]["symbol"]
    high = (await client.get("/api/v1/research/candidates", params={"min_score": 100})).json()["data"]
    assert high["items"] == [] and high["total"] == 0
    by_symbol = (
        await client.get("/api/v1/research/candidates", params={"sort": "symbol", "order": "asc"})
    ).json()["data"]["items"]
    assert [i["symbol"] for i in by_symbol] == sorted(SYMBOLS)
    sector = items[0]["sector"]
    assert [
        i["symbol"]
        for i in (await client.get("/api/v1/research/candidates", params={"sector": sector})).json()["data"][
            "items"
        ]
    ][0] == top
    assert (await client.get(f"/api/v1/research/candidates/{top}")).json()["data"]["symbol"] == top

    # ---- the report --------------------------------------------------------------------------------
    report = (await client.get(f"/api/v1/research/{top}")).json()["data"]
    assert (
        report["is_synthetic"] is True
        and report["data_confidence"] <= 30
        and report["research_score"] == items[0]["research_score"]
    )
    components = {c["key"]: c for c in report["score"]["components"]}
    assert len(components) == 10 and sum(c["max_points"] for c in components.values()) == 100
    assert (
        components["news_catalyst"]["available"] is False
        and components["news_catalyst"]["rating"] == "UNAVAILABLE"
    )
    assert (
        components["historical_setup"]["available"] is False and report["historical"] is None
    )  # Quick depth
    assert report["score_coverage_pct"] == 85.0 and report["verification"]["claims"] == []
    assert {"SYNTHETIC_DATA"} <= {w["code"] for w in report["warnings"]}
    assert (
        report["invalidation"] and report["why_listed"] and any("News" in n for n in report["not_assessed"])
    )
    assert "buy" not in json.dumps(report["labels"]).lower() and report["disclaimer"].startswith(
        "Research and decision support"
    )
    assert [a["status"] for a in report["agents"] if a["agent"] == "NewsCatalystAgent"] == ["NOT_AVAILABLE"]
    scanner_trace = next(a for a in report["agents"] if a["agent"] == "MarketScannerAgent")
    assert scanner_trace["status"] == "SUCCESS" and "not the research score" in scanner_trace["summary"]
    # every evidence item that names a source points at a source that exists in the report
    keys = {s["key"] for s in report["sources"]}
    assert all(
        e["source_key"] in keys
        for c in report["score"]["components"]
        for e in c["evidence"]
        if e["source_key"]
    )

    # ---- change the weights explicitly, then run again at Standard depth ----------------------------------------
    invalid = await client.post(
        "/api/v1/research/weights", json={"name": "Bad", "weights": {"liquidity": 100}}
    )
    assert invalid.status_code == 422
    weights = {c: v["max_points"] for c, v in components.items()}
    weights.update({"liquidity": 20, "news_catalyst": 5})
    proposed = await client.post(
        "/api/v1/research/weights", json={"name": "Liquidity heavy", "weights": weights, "notes": "test"}
    )
    assert proposed.status_code == 201 and proposed.json()["data"]["status"] == "PROPOSED"
    active_before = [
        w for w in (await client.get("/api/v1/research/weights")).json()["data"] if w["status"] == "ACTIVE"
    ]
    assert len(active_before) == 1 and active_before[0]["version"] == 1  # proposing changed nothing
    approved = await client.post(f"/api/v1/research/weights/{proposed.json()['data']['id']}/approve")
    assert approved.status_code == 200 and approved.json()["data"]["status"] == "ACTIVE"
    statuses = {
        w["version"]: w["status"] for w in (await client.get("/api/v1/research/weights")).json()["data"]
    }
    assert statuses == {1: "ARCHIVED", 2: "ACTIVE"}

    second_id = await start(client, container, depth="STANDARD", as_of=utcnow() - timedelta(hours=3))
    second = (await client.get(f"/api/v1/research/{top}", params={"run_id": second_id})).json()["data"]
    assert second["score"]["weight_set_version"] == 2
    assert {c["key"]: c["max_points"] for c in second["score"]["components"]}["liquidity"] == 20
    assert second["historical"] is not None and second["historical"]["sessions_analyzed"] >= 40
    claims = {c["key"]: c for c in second["verification"]["claims"]}
    assert set(claims) == {"price", "session_volume", "data_integrity"}
    assert all(c["status"] != "VERIFIED" for c in claims.values())  # one provider can never be 'verified'
    standard = (await client.get(f"/api/v1/research/runs/{second_id}")).json()["data"]
    assert {a["agent"]: a["status"] for a in standard["agents"]}[
        "DataVerificationAgent"
    ] == "SUCCESS" and standard["sources_checked"] >= 3

    # ---- history, score changes, market, sectors ------------------------------------------------------------------
    history = (await client.get(f"/api/v1/research/{top}/history")).json()["data"]
    assert len(history) == 2 and {h["run_id"] for h in history} == {run_id, second_id}
    changes = (await client.get(f"/api/v1/research/{top}/score-history")).json()["data"]
    assert len(changes["points"]) == 2 and len(changes["changes"]) == 1
    change = changes["changes"][0]
    assert change["from_run_id"] == run_id and change["to_run_id"] == second_id and change["reasons"]
    text = " | ".join(change["reasons"])
    assert (
        "Scoring weights changed from version 1 to version 2" in text
    )  # the approved weights, not the market, moved the score
    assert "Historical setup statistics were run in this scan" in text
    assert change["delta"] == pytest.approx(change["to_score"] - change["from_score"], abs=0.11)
    market = (await client.get("/api/v1/research/market")).json()["data"]
    regime = market["context"]["regime"]
    assert (
        market["is_synthetic"] is True
        and regime["label"] in ("STRONG_BULLISH", "BULLISH", "RANGE", "BEARISH", "STRONG_BEARISH")
        and regime["factors"]
    )
    assert {i["symbol"] for i in market["context"]["indices"]} == {"NIFTY", "BANKNIFTY"} and market[
        "context"
    ]["breadth"]["universe_size"] == 3
    sectors = (await client.get("/api/v1/research/sectors")).json()["data"]["sectors"]
    assert sectors and [s["rank"] for s in sectors] == list(range(1, len(sectors) + 1))
    summary = (await client.get("/api/v1/research/summary")).json()["data"]
    assert summary["latest_run"]["id"] == second_id and summary["active_run"] is None
    assert len((await client.get("/api/v1/research/runs")).json()["data"]) == 2

    # ---- slices, export, not-yet-available features -----------------------------------------------------------------------
    for path in ("technical", "risk", "sources"):
        assert (await client.get(f"/api/v1/research/{top}/{path}")).status_code == 200
    csv_response = await client.get(f"/api/v1/research/{top}/export", params={"format": "csv"})
    assert csv_response.status_code == 200 and csv_response.headers["content-disposition"].startswith(
        "attachment"
    )
    rows = list(csv.reader(io.StringIO(csv_response.text)))
    assert (
        rows[0] == ["section", "field", "value"]
        and any(r[0] == "score_component" for r in rows)
        and any(r[1] == "synthetic_data" and r[2] == "True" for r in rows)
    )
    exported = (await client.get(f"/api/v1/research/{top}/export")).json()
    assert exported["symbol"] == top and exported["research_score"] is not None
    for path in ("news", "fundamentals"):
        response = await client.get(f"/api/v1/research/{top}/{path}")
        assert (
            response.status_code == 501
            and response.json()["success"] is False
            and "not connected" in response.json()["status"]["description"].lower()
            or response.status_code == 501
        )


async def test_request_validation_and_not_found(research):
    _, client = research
    post = client.post
    assert (await post("/api/v1/research/run", json={"universe": "CUSTOM"})).status_code == 422
    unknown = await post("/api/v1/research/run", json={"universe": "CUSTOM", "symbols": ["NOSUCHCO"]})
    assert unknown.status_code == 422 and "NOSUCHCO" in unknown.json()["status"]["description"]
    assert (
        "Unknown universe"
        in (await post("/api/v1/research/run", json={"universe": "NIFTY999"})).json()["status"]["description"]
    )
    future = await post(
        "/api/v1/research/run",
        json={"universe": "NIFTY50", "as_of": (utcnow() + timedelta(days=1)).isoformat()},
    )
    assert future.status_code == 422 and "future" in future.json()["status"]["description"]
    ancient = await post(
        "/api/v1/research/run",
        json={"universe": "NIFTY50", "as_of": (utcnow() - timedelta(days=400)).isoformat()},
    )
    assert ancient.status_code == 422
    assert (
        await post("/api/v1/research/run", json={"universe": "NIFTY50", "depth": "EXTREME"})
    ).status_code == 422
    missing = await client.get("/api/v1/research/TCS")
    assert missing.status_code == 404 and "Run a research scan" in missing.json()["status"]["description"]
    assert (await client.get("/api/v1/research/runs/nope")).status_code == 404
    assert (await client.get("/api/v1/research/market")).status_code == 404
    empty = (await client.get("/api/v1/research/candidates")).json()["data"]
    assert empty["items"] == [] and empty["run"] is None


async def test_source_registry_and_universes(research):
    _, client = research
    sources = (await client.get("/api/v1/research/source-registry")).json()["data"]
    by_key = {s["key"]: s for s in sources}
    assert (
        by_key["nse"]["reliability_score"] == 1.0
        and by_key["nse"]["connected"] is False
        and by_key["simulated"]["connected"] is True
    )
    assert (
        by_key["simulated"]["reliability_score"] == 0.1 and by_key["moneycontrol"]["reliability_score"] == 0.8
    )
    updated = await client.put(
        f"/api/v1/research/source-registry/{by_key['moneycontrol']['id']}",
        json={"enabled": False, "reliability_score": 0.7},
    )
    assert updated.status_code == 200 and updated.json()["data"]["enabled"] is False
    assert (
        await client.put(
            f"/api/v1/research/source-registry/{by_key['nse']['id']}", json={"reliability_score": 1.5}
        )
    ).status_code == 422

    universes = (await client.get("/api/v1/research/universes")).json()["data"]
    assert {"name": "NIFTY50", "count": 50}.items() <= {
        k: v for k, v in universes[0].items() if k in ("name", "count")
    }.items()
    nifty = (await client.get("/api/v1/research/universes/NIFTY50")).json()["data"]
    assert (
        len(nifty["members"]) == 50
        and "approximate" in (nifty["note"] or "").lower()
        and all(m["sector"] for m in nifty["members"])
    )
    assert next(m for m in nifty["members"] if m["symbol"] == "RELIANCE")["company"]
    replaced = await client.put(
        "/api/v1/research/universes/WATCH",
        json={"members": [{"symbol": "tcs", "sector": "IT"}, {"symbol": "INFY"}]},
    )
    assert replaced.status_code == 200 and replaced.json()["data"]["count"] == 2
    assert (
        await client.put("/api/v1/research/universes/WATCH", json={"members": [{"symbol": "NOPE"}]})
    ).status_code == 422
    assert (
        await client.put("/api/v1/research/universes/CUSTOM", json={"members": [{"symbol": "TCS"}]})
    ).status_code == 422


async def test_runs_left_in_progress_are_failed_on_restart(research):
    container, client = research
    async with container.db.session_factory() as session:
        services = Services(session, container)
        run = await services.research_store.runs.create(
            ResearchRun(
                run_number=5000, status="RUNNING", universe="NIFTY50", depth="STANDARD", as_of=utcnow()
            )
        )
        await session.commit()
        run_id = run.id
    await TradingEngine(container).bootstrap()
    finished = (await client.get(f"/api/v1/research/runs/{run_id}")).json()["data"]
    assert finished["status"] == "FAILED" and "restarted" in finished["error_message"]
    # ...and a new run is not blocked by the dead one
    assert (
        await client.post(
            "/api/v1/research/run", json={"universe": "CUSTOM", "symbols": ["TCS"], "depth": "QUICK"}
        )
    ).status_code == 201
    await container.research_runner.shutdown()


async def test_candle_store_keeps_data_sources_apart(services):
    repo = services.candle_repo
    stamp = datetime(2026, 1, 5, 4, 0, tzinfo=UTC)
    bar = lambda close: [Candle(stamp, 100, 101, 99, close, 10)]  # noqa: E731
    assert await repo.save_candles("TCS", "NSE", Timeframe.M15, bar(100.0), "simulated") == 1
    assert (
        await repo.save_candles("TCS", "NSE", Timeframe.M15, bar(101.0), "dhan") == 1
    )  # same timestamp, different source: allowed
    assert (
        await repo.save_candles("TCS", "NSE", Timeframe.M15, bar(100.0), "simulated") == 0
    )  # not duplicated within a source
    start, end = stamp - timedelta(hours=1), stamp + timedelta(hours=1)
    assert [
        c.close for c in await repo.get_candles("TCS", "NSE", Timeframe.M15, start, end, source="dhan")
    ] == [101.0]
    assert [
        c.close for c in await repo.get_candles("TCS", "NSE", Timeframe.M15, start, end, source="simulated")
    ] == [100.0]
    assert (await repo.coverage("TCS", "NSE", Timeframe.M15, start, end, source="zerodha"))[0] == 0


async def test_only_administrators_can_approve_weights():
    settings = make_settings(auth_enabled=True, allow_registration=True, research_history_days=60)
    container = await build_container(settings, SimulatedMarketDataProvider(always_open=True))
    app = create_app(settings, container)
    app.state.container = container
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:

            async def register(email):  # noqa: ANN001, ANN202
                r = await client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": "correct-horse-1", "full_name": email},
                )
                return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}, r.json()["data"][
                    "user"
                ]["is_admin"]

            admin_headers, admin_flag = await register("admin@example.com")
            member_headers, member_flag = await register("member@example.com")
            assert admin_flag is True and member_flag is False
            body = {
                "name": "Proposal",
                "weights": {
                    "market_regime": 10,
                    "liquidity": 15,
                    "price_action": 15,
                    "momentum": 10,
                    "volume": 10,
                    "volatility": 10,
                    "technical_setup": 10,
                    "news_catalyst": 10,
                    "historical_setup": 5,
                    "risk": 5,
                },
            }
            proposal = await client.post("/api/v1/research/weights", json=body, headers=member_headers)
            assert proposal.status_code == 201  # anyone signed in may propose
            weight_id = proposal.json()["data"]["id"]
            assert (
                await client.post(f"/api/v1/research/weights/{weight_id}/approve", headers=member_headers)
            ).status_code == 403
            assert (await client.post(f"/api/v1/research/weights/{weight_id}/approve")).status_code == 401
            approved = await client.post(
                f"/api/v1/research/weights/{weight_id}/approve", headers=admin_headers
            )
            assert approved.status_code == 200 and approved.json()["data"]["approved_by"]
    finally:
        await container.close()


async def test_symbols_with_special_characters_route_correctly(research):
    container, client = research
    await start(client, container, depth="QUICK", symbols=["M&M", "BAJAJ-AUTO"])
    for encoded, symbol in (("M%26M", "M&M"), ("BAJAJ-AUTO", "BAJAJ-AUTO")):
        response = await client.get(f"/api/v1/research/{encoded}")
        assert response.status_code == 200 and response.json()["data"]["symbol"] == symbol
    assert (await client.get("/api/v1/research/M%26M/technical")).json()["data"]["symbol"] == "M&M"
    assert (await client.get("/api/v1/research/candidates/M%26M")).json()["data"]["symbol"] == "M&M"
