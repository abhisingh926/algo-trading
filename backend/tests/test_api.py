"""HTTP level: response envelope, auth, and the full user journey from the spec."""

from datetime import timedelta

import httpx

from app.main import create_app
from app.utils.time import ist_today
from tests.conftest import build_container, make_candles, make_settings

STRATEGY = {
    "name": "EMA Intraday",
    "strategy_type": "EMA_CROSSOVER",
    "symbol": "RELIANCE",
    "timeframe": "5m",
    "capital": 100000,
    "risk_per_trade": 0.01,
    "stop_loss_pct": 0.01,
    "target_pct": 0.02,
    "trading_mode": "PAPER",
    "parameters": {"fast_period": 5, "slow_period": 12},
}


def assert_envelope(body: dict, success: bool, code: int) -> None:
    assert set(body) == {"success", "message", "status", "data"}
    assert body["success"] is success and body["status"]["code"] == code and body["status"]["description"]


async def test_health_and_docs(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert_envelope(body, True, 200)
    assert body["data"] == {
        "status": "ok",
        "database": "ok",
        "trading_mode": "PAPER",
        "live_trading_enabled": False,
    }
    assert (await client.get("/openapi.json")).status_code == 200


async def test_error_envelopes(client):
    missing = await client.get("/api/v1/strategies/does-not-exist")
    assert missing.status_code == 404
    assert_envelope(missing.json(), False, 404)
    assert missing.json()["data"] is None

    invalid = await client.post("/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 0})
    assert invalid.status_code == 422
    assert_envelope(invalid.json(), False, 422)
    assert invalid.json()["data"]["errors"][0]["field"] == "quantity"

    limit_without_price = await client.post(
        "/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 1, "order_type": "LIMIT"}
    )
    assert limit_without_price.status_code == 422

    assert_envelope((await client.get("/api/v1/nope")).json(), False, 404)


async def test_risk_rejection_matches_spec_format(client):
    await client.put("/api/v1/risk", json={"max_order_value": 1000})
    response = await client.post("/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 10})
    body = response.json()
    assert response.status_code == 400 and body["message"] == "Unable to place order"
    assert "maximum order value" in body["status"]["description"] and body["data"]["order_id"]
    rejected = (await client.get("/api/v1/orders", params={"status_group": "rejected"})).json()["data"]
    assert [o["id"] for o in rejected] == [body["data"]["order_id"]]


async def test_full_paper_trading_journey(client, market_data):
    # 1-2. dashboard + paper broker
    status = (await client.get("/api/v1/system/status")).json()["data"]
    assert (
        status["trading_mode"] == "PAPER"
        and status["live_trading_enabled"] is False
        and status["system_state"] == "RUNNING"
    )
    brokers = (await client.get("/api/v1/brokers")).json()["data"]
    assert [b["broker_type"] for b in brokers] == ["PAPER"]
    created = await client.post(
        "/api/v1/brokers", json={"name": "My paper", "broker_type": "PAPER", "environment": "PAPER"}
    )
    assert created.status_code == 201
    test = (
        await client.post("/api/v1/brokers/test", json={"broker_account_id": created.json()["data"]["id"]})
    ).json()["data"]
    assert test["connected"] is True
    routing = (await client.get("/api/v1/brokers/status")).json()["data"]
    assert "PaperBroker" in routing["order_routing"] and not any(g["passed"] for g in routing["live_guards"])

    # 3-4. strategy with parameters
    types = (await client.get("/api/v1/strategies/types")).json()["data"]
    assert {t["type"] for t in types} == {"EMA_CROSSOVER", "VWAP", "BREAKOUT"}
    response = await client.post("/api/v1/strategies", json=STRATEGY)
    assert response.status_code == 201 and response.json()["message"] == "Strategy created successfully"
    strategy = response.json()["data"]
    assert strategy["parameters"] == {"fast_period": 5, "slow_period": 12} and strategy["status"] == "STOPPED"
    assert (await client.post("/api/v1/strategies", json=STRATEGY)).status_code == 409
    bad = await client.post(
        "/api/v1/strategies",
        json=STRATEGY | {"name": "bad", "parameters": {"fast_period": 50, "slow_period": 10}},
    )
    assert bad.status_code == 422 and "smaller" in bad.json()["status"]["description"]
    updated = await client.put(
        f"/api/v1/strategies/{strategy['id']}", json={"parameters": {"fast_period": 4, "slow_period": 9}}
    )
    assert updated.json()["data"]["parameters"] == {"fast_period": 4, "slow_period": 9}

    # 5-6. backtest + results
    closes = [100 + (i % 40) * 0.5 if (i // 40) % 2 == 0 else 120 - (i % 40) * 0.5 for i in range(400)]
    start_day = ist_today() - timedelta(days=5)
    from datetime import UTC, datetime, time

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
    assert run.status_code == 201
    backtest = run.json()["data"]
    assert backtest["status"] == "COMPLETED", backtest["error_message"]
    metrics = backtest["metrics"]
    assert metrics["total_trades"] > 0 and metrics["total_charges"] > 0 and metrics["data_source"] == "fake"
    assert metrics["final_capital"] == round(100000 + metrics["net_pnl"], 2)
    trades = (await client.get(f"/api/v1/backtests/{backtest['id']}/trades")).json()["data"]
    assert len(trades) == metrics["total_trades"] and {"entry_time", "exit_time", "net_pnl", "side"} <= set(
        trades[0]
    )
    curve = (await client.get(f"/api/v1/backtests/{backtest['id']}/equity-curve")).json()["data"]
    assert len(curve) > 10 and {"timestamp", "equity", "drawdown", "drawdown_pct"} == set(curve[0])
    report = (await client.get(f"/api/v1/backtests/{backtest['id']}/report")).json()["data"]
    assert report["backtest"]["id"] == backtest["id"] and report["monthly_returns"]
    assert [b["id"] for b in (await client.get("/api/v1/backtests")).json()["data"]] == [backtest["id"]]

    # 7. start in PAPER
    started = await client.post(f"/api/v1/strategies/{strategy['id']}/start")
    assert started.json()["data"]["status"] == "RUNNING"
    assert (await client.put(f"/api/v1/strategies/{strategy['id']}", json={"capital": 1})).status_code == 409
    assert (await client.delete(f"/api/v1/strategies/{strategy['id']}")).status_code == 409

    # 9-11. simulated order -> position -> P&L
    order = await client.post(
        "/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 10, "stop_loss": 980}
    )
    assert order.status_code == 201
    data = order.json()["data"]
    assert (data["status"], data["broker_type"], data["trading_mode"], data["pending_quantity"]) == (
        "FILLED",
        "PAPER",
        "PAPER",
        0,
    )
    detail = (await client.get(f"/api/v1/orders/{data['id']}")).json()["data"]
    assert [e["event_type"] for e in detail["events"]][-1] == "order_filled"
    positions = (await client.get("/api/v1/positions/RELIANCE")).json()["data"]
    assert positions[0]["quantity"] == 10 and positions[0]["side"] == "LONG"
    patched = await client.put(f"/api/v1/positions/{positions[0]['id']}", json={"target": 1100})
    assert patched.json()["data"]["target"] == 1100

    market_data.set_price("RELIANCE", 1050)
    closed = await client.post(f"/api/v1/positions/{positions[0]['id']}/close")
    assert closed.json()["data"]["status"] == "FILLED"
    trade = (await client.get("/api/v1/trades")).json()["data"][0]
    assert (
        trade["gross_pnl"] == 500 and (await client.get(f"/api/v1/trades/{trade['id']}")).status_code == 200
    )
    summary = (await client.get("/api/v1/dashboard/summary")).json()["data"]
    assert (
        summary["trades_today"] == 1
        and summary["realized_pnl_today"] == round(trade["net_pnl"], 2)
        and summary["running_strategies"] == 1
    )
    performance = (await client.get("/api/v1/dashboard/performance")).json()["data"]
    assert performance["total_trades"] == 1 and performance["win_rate"] == 100
    assert (await client.get("/api/v1/dashboard/pnl")).json()["data"]["daily"][0]["trades"] == 1

    # 12-13. stop + kill switch
    assert (await client.post(f"/api/v1/strategies/{strategy['id']}/stop")).json()["data"][
        "status"
    ] == "STOPPED"
    assert (
        await client.post("/api/v1/risk/kill-switch", json={"activate": True})
    ).status_code == 422  # needs confirm
    killed = await client.post(
        "/api/v1/risk/kill-switch", json={"activate": True, "confirm": True, "reason": "drill"}
    )
    assert killed.json()["data"]["kill_switch_active"] is True
    assert (await client.get("/api/v1/system/status")).json()["data"]["system_state"] == "HALTED"
    blocked = await client.post("/api/v1/orders", json={"symbol": "INFY", "side": "BUY", "quantity": 1})
    assert blocked.status_code == 400 and "Kill switch" in blocked.json()["status"]["description"]
    assert (await client.post(f"/api/v1/strategies/{strategy['id']}/start")).status_code == 423
    resumed = await client.post("/api/v1/risk/kill-switch", json={"activate": False, "confirm": True})
    assert resumed.json()["data"]["kill_switch_active"] is False

    # 14. events
    events = (await client.get("/api/v1/events", params={"limit": 200})).json()["data"]
    assert {
        "strategy_started",
        "strategy_stopped",
        "order_filled",
        "kill_switch_activated",
        "backtest_completed",
    } <= {e["event_type"] for e in events}


async def test_market_data_endpoints(client, market_data):
    instruments = (await client.get("/api/v1/market-data/instruments", params={"search": "REL"})).json()[
        "data"
    ]
    assert [i["symbol"] for i in instruments] == ["RELIANCE"]
    quotes = (await client.get("/api/v1/market-data/quotes", params={"symbols": "RELIANCE,INFY"})).json()[
        "data"
    ]
    assert {q["symbol"]: q["ltp"] for q in quotes} == {"RELIANCE": 1000, "INFY": 1500}
    created = await client.post(
        "/api/v1/market-data/instruments",
        json={"symbol": "tatasteel", "name": "Tata Steel", "exchange_token": "3499"},
    )
    assert created.status_code == 201 and created.json()["data"]["symbol"] == "TATASTEEL"
    assert (
        await client.post("/api/v1/market-data/instruments", json={"symbol": "TATASTEEL"})
    ).status_code == 409


async def test_authentication_flow(market_data):
    container = await build_container(make_settings(auth_enabled=True), market_data)
    app = create_app(container.settings, container)
    app.state.container = container
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            assert (await http.get("/api/v1/auth/status")).json()["data"] == {
                "auth_enabled": True,
                "registration_open": True,
                "has_users": False,
            }
            denied = await http.get("/api/v1/strategies")
            assert denied.status_code == 401
            assert_envelope(denied.json(), False, 401)
            assert (
                await http.post("/api/v1/orders", json={"symbol": "RELIANCE", "side": "BUY", "quantity": 1})
            ).status_code == 401

            weak = await http.post(
                "/api/v1/auth/register",
                json={"email": "a@example.com", "password": "short", "full_name": "A"},
            )
            assert weak.status_code == 422
            registered = await http.post(
                "/api/v1/auth/register",
                json={"email": "Admin@Example.com", "password": "correct-horse-1", "full_name": "Admin"},
            )
            assert registered.status_code == 201
            user = registered.json()["data"]["user"]
            assert (
                user["is_admin"] is True
                and user["email"] == "admin@example.com"
                and "hashed_password" not in user
            )

            second = await http.post(
                "/api/v1/auth/register",
                json={"email": "b@example.com", "password": "correct-horse-2", "full_name": "B"},
            )
            assert second.status_code == 403  # registration closes after the first admin

            assert (
                await http.post(
                    "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-password"}
                )
            ).status_code == 401
            login = await http.post(
                "/api/v1/auth/login", json={"email": "admin@example.com", "password": "correct-horse-1"}
            )
            token = login.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            assert (await http.get("/api/v1/auth/me", headers=headers)).json()["data"][
                "email"
            ] == "admin@example.com"
            assert (await http.get("/api/v1/strategies", headers=headers)).status_code == 200
            assert (
                await http.get("/api/v1/strategies", headers={"Authorization": "Bearer garbage"})
            ).status_code == 401
    finally:
        await container.close()


async def test_no_endpoint_leaks_credentials(market_data):
    secret = "dhan-token-that-must-never-leave-the-backend"
    container = await build_container(
        make_settings(dhan_client_id="1000000001", dhan_access_token=secret), market_data
    )
    app = create_app(container.settings, container)
    app.state.container = container
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            for path in (
                "/api/v1/brokers",
                "/api/v1/brokers/status",
                "/api/v1/system/config",
                "/api/v1/system/status",
                "/health",
            ):
                body = (await http.get(path)).text
                assert secret not in body and "1000000001" not in body, path
            config = (await http.get("/api/v1/system/config")).json()["data"]
            assert config["brokers_configured"] == {"DHAN": True, "ZERODHA": False, "FYERS": False}
    finally:
        await container.close()
