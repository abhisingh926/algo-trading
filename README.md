# Algo Trading Platform (Indian markets)

A modular algorithmic trading platform for NSE/BSE equities: strategy engine, risk management, order
management, paper trading, backtesting with realistic costs, and a Next.js trading dashboard.

> **Built for development, backtesting and paper/sandbox trading.**
> The default mode is `PAPER`. Live trading is **disabled** and needs four independent switches
> (three environment variables plus an in-application arming step) before a single real order can be sent.
> Nothing here is investment advice. Backtest and paper results do not predict live results.

```
==============================================
  Trading Mode: PAPER

  LIVE TRADING: DISABLED
==============================================
```

## Contents

1. [User guide for new users](docs/USER_GUIDE.md)
2. [Architecture](#architecture)
3. [Quick start with Docker](#quick-start-with-docker)
4. [Local development setup](#local-development-setup)
5. [Environment variables](#environment-variables)
6. [Database migrations](#database-migrations)
7. [Running tests](#running-tests)
8. [Paper trading walkthrough](#paper-trading-walkthrough)
9. [New users and the good-practice review](#new-users-and-the-good-practice-review)
10. [Backtesting](#backtesting)
11. [Trading modes and the live trading guards](#trading-modes-and-the-live-trading-guards)
12. [Dhan sandbox configuration](#dhan-sandbox-configuration)
13. [Adding a broker](#adding-a-broker)
14. [Logging and observability](#logging-and-observability)
15. [Production deployment considerations](#production-deployment-considerations)
16. [Known limitations](#known-limitations)

## Architecture

```mermaid
flowchart LR
    UI["Next.js dashboard<br/>(TanStack Query)"] -->|"REST /api/v1 + JWT"| API

    subgraph Backend["FastAPI backend"]
        API["Routers<br/>(no business logic)"] --> SVC["Services"]
        SVC --> REPO["Repositories"]
        REPO --> ORM["SQLAlchemy 2 async"]

        WK["Workers<br/>market data · strategy · order monitor"] --> ENG["TradingEngine"]
        ENG --> SVC

        SVC --> STRAT["Strategies<br/>EMA · VWAP · Breakout"]
        SVC --> RISK["RiskManager +<br/>PositionSizer"]
        SVC --> OM["OrderManager /<br/>PositionManager"]
        OM --> REG{"BrokerRegistry<br/>(mode + live guards)"}
        SVC --> BT["BacktestEngine +<br/>BrokerSimulator"]
        SVC --> MD["MarketDataProvider"]
    end

    REG -->|PAPER: always| PAPER["PaperBroker"]
    REG -->|SANDBOX| DHANS["DhanBroker (sandbox URL)"]
    REG -->|"LIVE: all 4 guards"| LIVE["DhanBroker / ZerodhaBroker"]
    PAPER --> MD
    MD --> SIM["Simulated feed"]
    MD --> DHANMD["Dhan / Zerodha data API"]
    ORM --> DB[("MySQL 8")]
    MD -.->|latest quotes| REDIS[("Redis")]
```

### Order path

```mermaid
flowchart TD
    S["Strategy signal / manual order"] --> P["Persist order (CREATED)"]
    P --> R{"RiskManager"}
    R -- rejected --> X["Order REJECTED + event (never reaches a broker)"]
    R -- approved --> G{"BrokerRegistry"}
    G -- "mode/guard mismatch" --> X
    G --> B["Broker adapter .place_order()<br/>retry on transport errors"]
    B --> F["Fills → Position → Trade → Daily P&L"]
```

### Layering rules

| Layer | Location | Rule |
|---|---|---|
| Routers | `backend/app/api/v1` | Parse/validate HTTP, call one service, wrap the response. No queries, no business logic. |
| Services | `backend/app/services` | Business logic and orchestration. Built per request by `services/factory.py`. |
| Repositories | `backend/app/repositories` | The only code that talks to SQLAlchemy. |
| Domain | `backend/app/domain` | Broker-neutral enums and value objects. |
| Brokers | `backend/app/brokers` | `BrokerInterface` + adapters. Broker vocabulary lives only in each adapter's `mapper.py`. |
| Strategies | `backend/app/strategies` | Pure functions of candles. No broker, DB or order knowledge. |
| Risk | `backend/app/risk` | Pure `RiskManager` and `PositionSizer`. |
| Trading | `backend/app/trading` | Order/position/portfolio managers, charges model, engine cycles. |
| Backtesting | `backend/app/backtesting` | Bar engine, execution simulator, metrics, report. |
| Workers | `backend/app/workers` | Thin periodic schedulers around `TradingEngine`. |

The full API contract is in [docs/API_CONTRACT.md](docs/API_CONTRACT.md). Interactive docs: `http://localhost:8000/docs`.

### Project structure

```
├── backend/
│   ├── app/
│   │   ├── main.py, container.py        app factory, process-wide singletons
│   │   ├── core/                        config, database, security, logging, exceptions, dependencies, cache
│   │   ├── domain/                      enums.py, types.py
│   │   ├── models/ repositories/ schemas/ services/
│   │   ├── brokers/                     base.py, registry.py, http.py, paper/, dhan/, zerodha/
│   │   ├── market_data/                 base.py, simulated.py, factory.py
│   │   ├── strategies/ risk/ trading/ backtesting/ workers/ utils/
│   │   └── api/v1/
│   ├── alembic/                         migrations
│   ├── tests/                           164 tests, no network, no real broker
│   └── Dockerfile
├── frontend/                            Next.js App Router, Tailwind, shadcn/ui, TanStack Query, Recharts
├── docs/API_CONTRACT.md, docs/USER_GUIDE.md
├── docker-compose.yml  Makefile  .env.example
```

## Prerequisites

* Docker Desktop (for the one-command setup), **or**
* Python 3.11+, Node.js 20+, MySQL 8+, Redis 7 (Redis is optional; the quote cache falls back to memory)

## Quick start with Docker

```bash
cp .env.example .env
# fill in the three required secrets:
#   MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD   -> e.g. `openssl rand -hex 16`
#   SECRET_KEY                            -> `openssl rand -hex 32`
docker compose up -d
```

| URL | What |
|---|---|
| http://localhost:3000 | Dashboard |
| http://localhost:8000 | Backend |
| http://localhost:8000/docs | Swagger |
| http://localhost:8000/health | Health |

The backend container runs `alembic upgrade head` on every start, seeds the paper broker account, the
default risk configuration and a small NSE instrument master.

On first visit the UI asks you to **create the first admin account**. Registration closes afterwards
unless `ALLOW_REGISTRATION=true`. For throwaway local use you may set `AUTH_ENABLED=false`.

If ports 3000 / 8000 / 3306 / 6379 are taken on your machine, change `FRONTEND_PORT`, `BACKEND_PORT`,
`MYSQL_HOST_PORT`, `REDIS_HOST_PORT` in `.env`. When you change the frontend port, add the new origin to
`CORS_ORIGINS`; when you change the backend port, update `NEXT_PUBLIC_API_URL` and rebuild the frontend.

## Local development setup

### MySQL and Redis

Easiest: `docker compose up -d mysql redis`. With a native MySQL instead:

```sql
CREATE DATABASE algo_trading CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'algo'@'%' IDENTIFIED BY '<password>';
GRANT ALL PRIVILEGES ON algo_trading.* TO 'algo'@'%';
```

Set `DATABASE_URL=mysql+aiomysql://algo:<password>@127.0.0.1:3306/algo_trading` in `.env`.
Redis: `brew install redis && brew services start redis` (or leave it out).

### Python backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The backend reads `.env` from the repository root.

### Node frontend

```bash
cd frontend
npm ci
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

`make help` lists shortcuts for all of the above.

## Environment variables

All configuration is loaded by Pydantic Settings (`backend/app/core/config.py`). `.env` is git-ignored;
`.env.example` documents every variable and contains no secrets.

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `production` makes `SECRET_KEY` mandatory |
| `DATABASE_URL` | – | `mysql+aiomysql://user:pass@host:3306/db` |
| `MYSQL_*` | – | Used by docker compose to create the database and build the container `DATABASE_URL` |
| `REDIS_URL` | `redis://localhost:6379/0` | Quote cache mirror (optional) |
| `SECRET_KEY` | – | JWT signing key. Empty in development → ephemeral key + warning |
| `AUTH_ENABLED` / `ALLOW_REGISTRATION` | `true` / `false` | JWT auth; first user becomes admin |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma separated |
| **`TRADING_MODE`** | **`PAPER`** | `BACKTEST` · `PAPER` · `SANDBOX` · `LIVE` |
| **`ENABLE_LIVE_TRADING`** | **`false`** | Live guard 2 |
| **`LIVE_TRADING_CONFIRMATION`** | empty | Live guard 3, must equal `I-ACCEPT-REAL-MONEY-RISK` |
| `MARKET_DATA_PROVIDER` | `simulated` | `simulated` · `dhan` · `zerodha` (falls back to simulated without credentials) |
| `SIMULATED_MARKET_24X7` | `true` | Synthetic feed ignores NSE hours so paper trading works any time |
| `PAPER_INITIAL_CAPITAL`, `PAPER_SLIPPAGE_PCT`, `PAPER_MAX_FILL_QTY_PER_TICK` | `500000`, `0.0005`, `0` | Paper broker behaviour (`>0` fill cap simulates partial fills) |
| `MAX_DAILY_LOSS`, `MAX_RISK_PER_TRADE`, `MAX_OPEN_POSITIONS`, `MAX_TRADES_PER_DAY`, `MAX_POSITION_SIZE`, `MAX_ORDER_VALUE`, `MAX_CONSECUTIVE_LOSSES`, `MAX_STRATEGY_DRAWDOWN` | see `.env.example` | **Seed** values for the risk configuration row. After first start, edit limits in the UI (Risk page) or `PUT /api/v1/risk` |
| `RUN_WORKERS`, `STRATEGY_POLL_SECONDS`, `ORDER_MONITOR_POLL_SECONDS`, `MARKET_DATA_POLL_SECONDS` | `true`, `10`, `3`, `3` | Background workers |
| `DHAN_*`, `ZERODHA_*`, `FYERS_*` | empty | Broker credentials. All optional. Never sent to the frontend, never logged, never stored in MySQL |

## Database migrations

```bash
cd backend
.venv/bin/alembic upgrade head                                   # apply
.venv/bin/alembic revision --autogenerate -m "describe change"   # create after editing models
.venv/bin/alembic downgrade -1                                   # roll back one
.venv/bin/alembic check                                          # fail if models and DB drifted
```

The initial revision lives in `backend/alembic/versions/`. Timestamps are stored as UTC `DATETIME(6)`;
money as `DECIMAL(18,4)`; primary keys are UUID strings.

## Running tests

```bash
cd backend && .venv/bin/pytest -q          # or: make test
cd frontend && npm run lint && npx tsc --noEmit
```

Tests use in-memory SQLite, a fake market data provider and `httpx.MockTransport` for Dhan/Zerodha. They
cannot reach a real broker. Coverage by area:

| File | Covers |
|---|---|
| `test_strategies.py` | EMA crossover, VWAP (session + rolling), breakout, parameter validation |
| `test_risk.py` | every risk limit, exits always allowed, position sizing incl. the ₹5,00,000 / 1% / 20-rupee-stop = 250 example |
| `test_paper_broker.py` | MARKET / LIMIT / SL / SL-M, partial fills, rejections, modify, cancel, funds |
| `test_orders.py` | order pipeline, risk rejection persistence, partial fills, cancel, modify, retries, protective exits |
| `test_trading_engine.py` | candles → signal → sizing → order → position → target exit, idempotency, worker error isolation |
| `test_backtesting.py` | P&L, no look-ahead, stops/targets/gaps, slippage, charges, win rate, drawdown, Sharpe guard |
| `test_dhan_broker.py` | mocked Dhan + Zerodha APIs, status mapping, error mapping, secret redaction in logs |
| `test_safety.py` | PAPER never reaches a real broker, every live guard, kill switch |
| `test_api.py` | response envelope, auth, full user journey, no credential leakage |

## Paper trading walkthrough

1. Open the dashboard. The top bar shows `PAPER` and `LIVE TRADING: DISABLED`.
2. **Brokers** → a "Paper Broker" account already exists. "Test connection" confirms it.
3. **Strategies → Create Strategy**: EMA Crossover, symbol `RELIANCE`, timeframe `1m`, fast `3`, slow `8`,
   capital ₹1,00,000, risk 1%, stop loss 0.3%, target 0.6%, mode PAPER. (Short periods on the 1-minute
   timeframe produce a signal roughly every 10–15 minutes on the simulated feed.)
4. **Backtest** it, then **Start** (a confirmation dialog appears).
5. The strategy worker evaluates each newly closed candle. A BUY signal is sized by the `PositionSizer`,
   checked by the `RiskManager`, and sent to the `PaperBroker`, which fills against the market data feed
   with slippage. Positions, P&L, orders, signals and the event log update live.
6. Stop loss / target exits are fired by the order monitor worker. Stop the strategy, or hit the
   **Kill switch**: strategies stop, working orders are cancelled, new entries are blocked, the system shows
   `HALTED`. Open positions are **not** closed unless "close positions on kill switch" is enabled in Risk.
   Exits are always allowed while halted.

The same flow over HTTP (with `AUTH_ENABLED=false`, otherwise add a bearer token):

```bash
curl -X POST localhost:8000/api/v1/orders -H 'content-type: application/json' \
  -d '{"symbol":"RELIANCE","side":"BUY","quantity":10,"stop_loss":1400}'
```

The response description reads `PAPER order FILLED via PAPER`.

## New users and the good-practice review

[docs/USER_GUIDE.md](docs/USER_GUIDE.md) is a plain-language guide, also shown in the app under **Guide**.
The Guide page has a getting-started checklist derived from what the user has actually done
(`GET /api/v1/guide/onboarding`).

The **good-practice review** (`POST /api/v1/strategies/review`, `GET /api/v1/strategies/{id}/review`) grades a
strategy setup as `RECOMMENDED`, `CAUTION` or `NOT_RECOMMENDED` with explained checks: risk per trade, stop loss,
reward to risk, timeframe and costs, indicator settings, backtest quality (length, trade count, profit factor,
drawdown, costs, synthetic data, staleness) and, for real-money modes, the paper trading record.
It is advisory only and never blocks an action. Thresholds are constants in
`backend/app/risk/strategy_review.py` and are covered by `tests/test_review.py`.

## Backtesting

`POST /api/v1/backtests` (or the Backtesting page). Inputs: strategy, symbol, timeframe, date range,
capital, brokerage, slippage, statutory charges toggle. Candles are fetched from the market data provider
once and stored in MySQL (`candles` table); later runs read from the database.

Realism rules enforced by the engine:

* A signal on the close of bar *N* fills at the **open of bar N+1**. No look-ahead.
* Every fill pays slippage and the charges model: brokerage `min(0.03%, ₹20)` per order, STT on sells,
  exchange transaction charges, SEBI fees, stamp duty on buys and 18% GST. All rates are configurable.
* Stop loss and target are checked intrabar. If both are touched in one bar the **stop** is assumed first.
  Gaps through a level fill at the bar open.
* Position size comes from the same `PositionSizer` the live engine uses, with no leverage.
* Sharpe ratio is reported only with at least 20 daily return observations; otherwise it is `null`.

Outputs: initial/final capital, net P&L, gross profit/loss, trade counts, win rate, profit factor, max
drawdown, average / largest trades, Sharpe, total charges, total slippage, trades, equity and drawdown
curves, monthly returns. `metrics.data_source` tells you whether the data was `simulated`.

## Trading modes and the live trading guards

| Mode | Orders go to | Requirements |
|---|---|---|
| `BACKTEST` | nowhere (order placement is refused) | – |
| `PAPER` (default) | `PaperBroker`, always | none. Configured broker credentials are irrelevant |
| `SANDBOX` | broker sandbox API (Dhan) | `TRADING_MODE=SANDBOX`, a SANDBOX broker account, credentials |
| `LIVE` | real broker | **all four guards below** |

Live trading needs every one of these. Changing any single variable does nothing:

1. `TRADING_MODE=LIVE`
2. `ENABLE_LIVE_TRADING=true`
3. `LIVE_TRADING_CONFIRMATION=I-ACCEPT-REAL-MONEY-RISK`
4. A LIVE broker account **armed inside the application**. There is deliberately no button for this:

   ```bash
   curl -X POST localhost:8000/api/v1/brokers/<account_id>/arm-live \
     -H "Authorization: Bearer <token>" -H 'content-type: application/json' \
     -d '{"armed": true, "confirmation": "I-ACCEPT-REAL-MONEY-RISK"}'
   ```

Enforcement is layered: `BrokerRegistry.resolve_for_order` is the single routing choke point, and each real
adapter re-checks the guard inside `place_order`/`modify_order`. A strategy whose own mode is `PAPER` stays
on the paper broker even when the platform runs in `LIVE`. `GET /api/v1/brokers/status` shows each guard.
All of this is covered by `tests/test_safety.py`.

## Dhan sandbox configuration

1. Create a DhanHQ developer/sandbox account at the DhanHQ developer portal and generate a **sandbox**
   access token. Sandbox tokens are separate from your live trading token.
2. In `.env`:

   ```env
   TRADING_MODE=SANDBOX
   DHAN_CLIENT_ID=<your client id>
   DHAN_ACCESS_TOKEN=<sandbox access token>
   # DHAN_SANDBOX_BASE_URL=https://sandbox.dhan.co/v2   (default)
   ```

3. Restart the backend. **Brokers → Add broker account**: type `DHAN`, environment `SANDBOX`. Run
   "Test connection".
4. Create a strategy with trading mode `SANDBOX` and that broker account, or place a manual order. Orders
   go to the sandbox base URL only; the live URL is unreachable in this mode.
5. Market data: the sandbox does not serve quotes. Keep `MARKET_DATA_PROVIDER=simulated`, or set it to
   `dhan` with a token that has the Data API subscription (read-only, cannot place orders).

Instruments need the exchange token (Dhan `securityId`) in the instrument master. Fourteen NSE large caps
are seeded; add more under `POST /api/v1/market-data/instruments`.

## Adding a broker

1. Create `backend/app/brokers/<name>/` with `client.py` (extend `BrokerHttpClient`), `mapper.py` (all
   vendor vocabulary), `orders.py`, `market_data.py` (implement `MarketDataProvider`) and `broker.py`
   (implement `BrokerInterface`, accept a `live_guard` callable and call it before sending orders).
2. Register it in `brokers/registry.py`: `SUPPORTED_ENVIRONMENTS` and `_build`.
3. Add credentials to `Settings` and `broker_credentials_configured`, plus `.env.example`.
4. Add tests with `httpx.MockTransport`, modelled on `tests/test_dhan_broker.py`.

Nothing in the engine, strategies, risk or API changes.

## Logging and observability

* JSON logs on stdout (`LOG_FORMAT=json`); one line per event with structured fields.
* Trading events: `strategy_started`, `strategy_stopped`, `signal_generated`, `risk_check_passed`,
  `risk_check_failed`, `order_submitted`, `order_filled`, `order_partially_filled`, `order_rejected`,
  `order_cancelled`, `order_failed`, `position_opened`, `position_closed`, `broker_connected`,
  `broker_disconnected`, `kill_switch_activated`, `kill_switch_deactivated`, `backtest_completed`.
  They are also persisted in `system_events` and shown on the **Logs** page. Every order additionally has
  its own audit trail in `order_events`.
* A redaction step masks any field whose key looks like a token, secret, password, API key or
  authorization header. Broker clients never log headers, and `httpx` request logging is silenced.
* Logging is stdlib `logging`, so SigNoz / OpenTelemetry integration is one extra handler in
  `core/logging.py:configure_logging` (plus `opentelemetry-instrument` for FastAPI, SQLAlchemy and httpx).

## Production deployment considerations

* **One worker process.** Run the API with `RUN_WORKERS=false` (scale it horizontally) and exactly one
  `python -m app.workers.runner`. Two worker processes would evaluate strategies twice. Add leader election
  (for example a Redis lock) before running more than one.
* **Secrets** from a secret manager, not a `.env` file. Set `APP_ENV=production` so a missing `SECRET_KEY`
  aborts startup. Rotate broker access tokens daily where the broker requires it.
* **TLS and auth.** Put the API behind a TLS-terminating reverse proxy, restrict `CORS_ORIGINS`, keep
  `AUTH_ENABLED=true`. Consider httpOnly cookies instead of localStorage tokens, plus 2FA, before exposing
  the UI beyond a private network.
* **Database.** Managed MySQL with backups and point-in-time recovery. Run migrations as a release step
  rather than on container start once there is more than one backend replica.
* **Market data.** Replace REST polling with the broker WebSocket feed (override
  `MarketDataProvider.subscribe`). Move bars/ticks to a time-series store by replacing
  `MarketDataRepository`; ticks are never written to MySQL today.
* **Reconciliation.** Before live use, add a startup and periodic reconciliation of platform positions
  against `broker.get_positions()`, and broker-side stop-loss orders so protection does not depend on this
  process being alive.
* **Monitoring.** Alert on `order_failed`, `risk_check_failed`, `strategy_error`, worker heartbeat loss
  (`/api/v1/system/status`) and kill switch activation.

## Known limitations

* The Dhan and Zerodha adapters are implemented against the documented REST APIs and tested with mocked
  HTTP only. They have **not** been exercised against the real services. Validate in the Dhan sandbox first.
* The Fyers adapter is not implemented (enum, settings and extension point exist).
* Live quotes are polled over REST. The Dhan binary WebSocket feed is not implemented.
* The simulated market data is synthetic. It is good for exercising the system and useless for judging a strategy.
* One position per (strategy, symbol, mode). No options/futures specifics (expiry, lot-based margin), no
  bracket/cover orders, no intraday auto square-off at 15:20.
* Paper and dashboard capital is computed from `PAPER_INITIAL_CAPITAL` plus realised P&L. Broker-reported
  funds are not yet used in SANDBOX/LIVE.
* Backtests run synchronously inside the request. Large ranges should move to a job queue.
* Stop loss and target are enforced by the order monitor worker at its poll interval, not by resting
  broker-side orders.
