# API Contract (v1)

Base URL: `http://localhost:8000` — all endpoints below are prefixed with `/api/v1`.
All JSON is `snake_case`. All timestamps are ISO-8601 UTC (`2026-09-18T10:00:00Z`). Dates are `YYYY-MM-DD`.
Money values are plain JSON numbers in INR. Percent-like config values are **fractions** (`0.01` = 1%)
unless the field name ends in `_pct_display`. Metrics named `*_pct` / `win_rate` are **percent numbers** (`71.4` = 71.4%).

## Envelope

Every response (success or error) uses the same envelope:

```json
{ "success": true, "message": "Strategy created successfully",
  "status": { "code": 201, "description": "Strategy created" }, "data": {} }
```

Errors: `success=false`, `data` is `null` or a small object with context (e.g. `{"order_id": "..."}`,
or `{"errors": [{"field": "quantity", "message": "..."}]}` for 422 validation errors).
HTTP status code always equals `status.code`.

## Auth

JWT bearer: `Authorization: Bearer <token>`. 401 → the frontend must clear the token and redirect to `/login`.

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/auth/status` (public) | – | `{auth_enabled, registration_open, has_users}` |
| POST | `/auth/register` (public, only while `registration_open`) | `{email, password (>=8), full_name}` | `AuthToken` |
| POST | `/auth/login` (public) | `{email, password}` | `AuthToken` |
| GET | `/auth/me` | – | `User` |

`AuthToken = {access_token, token_type: "bearer", expires_in (seconds), user: User}`
`User = {id, email, full_name, is_active, is_admin, created_at}`

If `auth_enabled` is `false`, no token is needed and the frontend must skip the login screen.
The first registered user becomes admin; afterwards registration closes unless `ALLOW_REGISTRATION=true`.

## System

| Method | Path | data |
|---|---|---|
| GET | `/health` (NOT under /api/v1, public) | `{status: "ok", database: "ok"|"error", trading_mode, live_trading_enabled}` (enveloped) |
| GET | `/system/status` | `SystemStatus` |
| GET | `/system/config` | `SystemConfig` (non-secret settings) |
| GET | `/events?limit=100&offset=0&event_type=&level=&strategy_id=` | `SystemEvent[]` (newest first) |

```
SystemStatus = {
  trading_mode: "BACKTEST"|"PAPER"|"SANDBOX"|"LIVE",
  live_trading_enabled: bool,
  kill_switch_active: bool,
  system_state: "RUNNING"|"HALTED",
  market_data_provider: "simulated"|"dhan"|"zerodha",
  server_time: datetime,
  components: [{ key: "broker"|"market_data"|"strategy_engine"|"order_engine"|"database"|"redis",
                 name: string,
                 status: "CONNECTED"|"DISCONNECTED"|"RUNNING"|"STOPPED"|"HALTED"|"NOT_CONFIGURED"|"DEGRADED",
                 detail: string|null }]
}
SystemConfig = { app_name, app_env, version, trading_mode, live_trading_enabled, auth_enabled, workers_enabled,
  market_data_provider, paper_initial_capital, paper_slippage_pct,
  strategy_poll_seconds, order_monitor_poll_seconds, market_data_poll_seconds,
  default_charges: ChargesConfig,
  brokers_configured: { "DHAN": bool, "ZERODHA": bool, "FYERS": bool } }
ChargesConfig = { brokerage_per_order, brokerage_pct, stt_sell_pct, exchange_txn_pct, sebi_pct, stamp_duty_buy_pct, gst_pct }
SystemEvent = { id, event_type, level: "INFO"|"WARNING"|"ERROR", message, payload: object|null,
  strategy_id: string|null, order_id: string|null, symbol: string|null, created_at }
```

Event types include: `strategy_started, strategy_stopped, signal_generated, risk_check_passed, risk_check_failed,
order_submitted, order_filled, order_partially_filled, order_rejected, order_cancelled, order_failed, position_opened,
position_closed, broker_connected, broker_disconnected, kill_switch_activated, kill_switch_deactivated, backtest_completed`.

## Dashboard

| Method | Path | data |
|---|---|---|
| GET | `/dashboard/summary` | `DashboardSummary` |
| GET | `/dashboard/pnl?days=30` | `{daily: DailyPnl[], equity_curve: EquityPoint[]}` |
| GET | `/dashboard/performance` | `Performance` |

```
DashboardSummary = { capital, available, used_margin, todays_pnl, realized_pnl_today, open_pnl, total_pnl,
  win_rate (percent, today+all-time closed trades), trades_today, open_positions, running_strategies,
  trading_mode, currency: "INR" }
DailyPnl   = { date, realized_pnl, unrealized_pnl, charges, net_pnl, trades, wins, losses }
EquityPoint = { timestamp, equity, realized_pnl, unrealized_pnl }
Performance = { total_trades, winning_trades, losing_trades, win_rate, gross_profit, gross_loss, net_pnl,
  profit_factor: number|null, average_trade, largest_win, largest_loss, max_drawdown, max_drawdown_pct, total_charges,
  by_strategy: [{strategy_id, strategy_name, trades, win_rate, net_pnl}] }
```

## Brokers

Broker credentials live ONLY in backend environment variables. No endpoint ever returns a credential.

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/brokers` | – | `BrokerAccount[]` |
| POST | `/brokers` | `{name, broker_type, environment, is_default?}` | `BrokerAccount` (201) |
| PUT | `/brokers/{id}` | `{name?, is_active?, is_default?}` | `BrokerAccount` |
| POST | `/brokers/{id}/arm-live` | `{armed: bool, confirmation: string}` | `BrokerAccount`. Application-level live guard; arming needs the phrase `I-ACCEPT-REAL-MONEY-RISK` and a LIVE account. Intentionally has no UI |
| DELETE | `/brokers/{id}` | – | `null` (the last paper account cannot be deleted) |
| GET | `/brokers/status` | – | `BrokerStatus` |
| POST | `/brokers/test` | `{broker_account_id}` | `BrokerTestResult` |

```
BrokerAccount = { id, name, broker_type: "PAPER"|"DHAN"|"ZERODHA"|"FYERS", environment: "PAPER"|"SANDBOX"|"LIVE",
  is_active, is_default, live_armed: bool, credentials_configured: bool,
  connection_status: "CONNECTED"|"DISCONNECTED"|"NOT_CONFIGURED"|"UNKNOWN",
  last_checked_at: datetime|null, last_error: string|null, created_at, updated_at }
BrokerStatus = { trading_mode, live_trading_enabled,
  live_guards: [{name, passed: bool, detail}],
  order_routing: string,   // human readable, e.g. "All orders are routed to PaperBroker"
  supported: [{broker_type, implemented: bool, credentials_configured: bool, environments: string[]}] }
BrokerTestResult = { broker_account_id, broker_type, connected: bool, latency_ms: number|null, detail: string }
```

## Strategies

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/strategies/types` | – | `StrategyTypeInfo[]` |
| GET | `/strategies` | – | `Strategy[]` |
| POST | `/strategies` | `StrategyCreate` | `Strategy` (201) |
| GET | `/strategies/{id}` | – | `Strategy` |
| PUT | `/strategies/{id}` | partial `StrategyCreate` | `Strategy` (409 if RUNNING) |
| DELETE | `/strategies/{id}` | – | `null` (409 if RUNNING) |
| POST | `/strategies/{id}/start` | – | `Strategy` |
| POST | `/strategies/{id}/stop` | – | `Strategy` |
| GET | `/strategies/{id}/signals?limit=50` | – | `Signal[]` |
| GET | `/signals?limit=50` | – | `Signal[]` |

```
StrategyTypeInfo = { type: "EMA_CROSSOVER"|"VWAP"|"BREAKOUT", name, description,
  parameters: [{ key, label, type: "int"|"float", default, min, max, description }] }
StrategyCreate = { name, strategy_type, symbol, exchange = "NSE", timeframe: "1m"|"5m"|"15m"|"1h"|"1d",
  capital, risk_per_trade (fraction), stop_loss_pct (fraction), target_pct (fraction|null),
  allow_short = false, trading_mode = "PAPER", broker_account_id: string|null, parameters: {key: number} }
Strategy = StrategyCreate + { id, status: "STOPPED"|"RUNNING"|"ERROR", broker_name: string|null,
  last_signal_at, last_evaluated_at, last_error,
  stats: { todays_pnl, total_pnl, trades, win_rate, open_position_qty }, created_at, updated_at }
Signal = { id, strategy_id, strategy_name, symbol, exchange, signal_type: "BUY"|"SELL"|"HOLD", price, reason,
  indicators: object, status: "GENERATED"|"EXECUTED"|"REJECTED"|"IGNORED", status_reason: string|null,
  order_id: string|null, candle_time, created_at }
```

## Orders

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/orders?status_group=all|open|filled|rejected|cancelled&symbol=&strategy_id=&limit=100&offset=0` | – | `Order[]` newest first |
| GET | `/orders/{id}` | – | `Order` with `events: OrderEvent[]` |
| POST | `/orders` | `OrderCreate` | `Order` (201). Risk/broker rejection → 400 with `data: {order_id}` |
| PUT | `/orders/{id}` | `{quantity?, price?, trigger_price?}` | `Order` |
| POST | `/orders/{id}/cancel` | – | `Order` |

```
OrderCreate = { symbol, exchange = "NSE", side: "BUY"|"SELL", order_type: "MARKET"|"LIMIT"|"SL"|"SL-M",
  product_type: "INTRADAY"|"DELIVERY" = "INTRADAY", quantity (int > 0), price?: number (LIMIT, SL),
  trigger_price?: number (SL, SL-M), stop_loss?: number, target?: number }
Order = { id, broker_order_id, broker_account_id, broker_type, strategy_id, strategy_name, symbol, exchange, side,
  order_type, product_type, quantity, filled_quantity, pending_quantity, price, trigger_price, average_fill_price,
  stop_loss, target,
  status: "CREATED"|"SUBMITTED"|"OPEN"|"TRIGGER_PENDING"|"PARTIALLY_FILLED"|"FILLED"|"CANCELLED"|"REJECTED"|"FAILED"|"EXPIRED",
  status_message, trading_mode, source: "MANUAL"|"STRATEGY"|"RISK_EXIT"|"KILL_SWITCH",
  retry_count, created_at, updated_at, events?: OrderEvent[] }
OrderEvent = { id, order_id, event_type, from_status, to_status, message, payload, created_at }
```
`status_group` mapping — open: CREATED, SUBMITTED, OPEN, TRIGGER_PENDING, PARTIALLY_FILLED; filled: FILLED;
rejected: REJECTED, FAILED; cancelled: CANCELLED, EXPIRED.

## Positions

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/positions?status=open|closed|all` (default open) | – | `Position[]` |
| GET | `/positions/{symbol}` | – | `Position[]` (open positions for the symbol) |
| PUT | `/positions/{id}` | `{stop_loss?: number|null, target?: number|null}` | `Position` |
| POST | `/positions/{id}/close` | – | `Order` (the market exit order) |

```
Position = { id, symbol, exchange, strategy_id, strategy_name, side: "LONG"|"SHORT", quantity, average_entry_price,
  last_price, unrealized_pnl, realized_pnl, stop_loss, target, status: "OPEN"|"CLOSED", trading_mode,
  opened_at, closed_at, updated_at }
```

## Trades (closed round trips)

| Method | Path | data |
|---|---|---|
| GET | `/trades?strategy_id=&symbol=&limit=100&offset=0` | `Trade[]` newest first |
| GET | `/trades/{id}` | `Trade` |

```
Trade = { id, position_id, strategy_id, strategy_name, symbol, exchange, side: "LONG"|"SHORT", quantity,
  entry_price, exit_price, entry_time, exit_time, gross_pnl, charges, net_pnl,
  exit_reason: "SIGNAL"|"STOP_LOSS"|"TARGET"|"MANUAL"|"KILL_SWITCH", trading_mode, created_at }
```

## Backtests

| Method | Path | Body | data |
|---|---|---|---|
| POST | `/backtests` | `BacktestCreate` | `Backtest` (201, already COMPLETED or FAILED — runs synchronously) |
| GET | `/backtests?limit=50` | – | `Backtest[]` newest first |
| GET | `/backtests/{id}` | – | `Backtest` |
| GET | `/backtests/{id}/trades` | – | `BacktestTrade[]` |
| GET | `/backtests/{id}/equity-curve` | – | `BacktestEquityPoint[]` |
| GET | `/backtests/{id}/report` | – | `{backtest, trades, equity_curve, monthly_returns: [{month: "YYYY-MM", net_pnl, trades}]}` |
| DELETE | `/backtests/{id}` | – | `null` |

```
BacktestCreate = { name?: string, strategy_id?: string,
  // required when strategy_id is absent, otherwise default from the strategy:
  strategy_type?, parameters?, symbol?, exchange? = "NSE", timeframe?, risk_per_trade?, stop_loss_pct?, target_pct?, allow_short?,
  start_date, end_date, initial_capital,
  brokerage_per_order = 20, brokerage_pct = 0.0003, slippage_pct = 0.0005, include_statutory_charges = true }
Backtest = { id, name, strategy_id, strategy_type, parameters, symbol, exchange, timeframe, start_date, end_date,
  status: "PENDING"|"RUNNING"|"COMPLETED"|"FAILED", error_message, initial_capital,
  config: { risk_per_trade, stop_loss_pct, target_pct, allow_short, slippage_pct, charges: ChargesConfig },
  metrics: BacktestMetrics|null, created_at, completed_at }
BacktestMetrics = { final_capital, net_pnl, total_return_pct, gross_profit, gross_loss, total_trades, winning_trades,
  losing_trades, win_rate, profit_factor: number|null, max_drawdown, max_drawdown_pct, average_trade,
  largest_win, largest_loss, sharpe_ratio: number|null, total_charges, total_slippage, candles_processed, data_source }
BacktestTrade = { id, entry_time, exit_time, symbol, side: "LONG"|"SHORT", entry_price, exit_price, quantity,
  gross_pnl, charges, net_pnl, exit_reason }
BacktestEquityPoint = { timestamp, equity, drawdown, drawdown_pct }
```

## Risk

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/risk` | – | `RiskConfiguration` |
| PUT | `/risk` | partial limits | `RiskConfiguration` |
| GET | `/risk/status` | – | `RiskStatus` |
| POST | `/risk/kill-switch` | `{activate: bool, confirm: true, reason?: string}` | `KillSwitchResult` |

```
RiskConfiguration = { id, max_risk_per_trade (fraction), max_daily_loss (INR), max_trades_per_day, max_open_positions,
  max_position_size (qty), max_order_value (INR), max_consecutive_losses, max_strategy_drawdown (fraction),
  close_positions_on_kill_switch: bool, kill_switch_active, kill_switch_activated_at, kill_switch_reason, updated_at }
RiskStatus = { kill_switch_active, system_state: "RUNNING"|"HALTED", trading_allowed: bool, blocked_reasons: string[],
  usage: [{ key, label, current, limit, utilization (0..1), breached: bool, unit: "INR"|"count" }] }
KillSwitchResult = { kill_switch_active, strategies_stopped, orders_cancelled, positions_closed, message }
```

## Market data

| Method | Path | Body | data |
|---|---|---|---|
| GET | `/market-data/instruments?search=&limit=50` | – | `Instrument[]` |
| POST | `/market-data/instruments` | `{symbol, exchange, name, exchange_token?, lot_size=1, tick_size=0.05}` | `Instrument` |
| GET | `/market-data/quotes?symbols=RELIANCE,INFY&exchange=NSE` | – | `Quote[]` |
| GET | `/market-data/candles?symbol=&exchange=NSE&timeframe=5m&start=&end=&limit=500` | – | `Candle[]` |
| POST | `/market-data/historical/sync` | `{symbol, exchange, timeframe, start_date, end_date}` | `{stored, total, source}` |

```
Instrument = { id, symbol, exchange, name, segment, exchange_token, lot_size, tick_size, is_active }
Quote = { symbol, exchange, ltp, open, high, low, close, volume, timestamp, source }
Candle = { timestamp, open, high, low, close, volume }
```

## Conventions and clarifications

* **CORS**: the backend allows the origins in `CORS_ORIGINS` with the `Authorization` header.
* **Nullability**: `Order.price / trigger_price / average_fill_price / broker_order_id / broker_account_id /
  strategy_id / strategy_name / stop_loss / target / status_message`, `Position.last_price / stop_loss / target /
  strategy_id / strategy_name / closed_at`, `Trade.position_id / strategy_id / strategy_name`,
  `Strategy.target_pct / broker_account_id / broker_name / last_*`, `OrderEvent.from_status / to_status / message /
  payload` may be `null`.
* **Signs**: `BacktestEquityPoint.drawdown` and `drawdown_pct` are `<= 0`. `max_drawdown` and `max_drawdown_pct`
  are positive magnitudes. `gross_loss` and `largest_loss` are `<= 0`.
* **`PUT /positions/{id}`**: an omitted field is unchanged, an explicit `null` clears the level.
* **Kill switch**: deactivating does not restart strategies. Position-reducing orders are accepted while halted.
* **`metrics.data_source`**: the market data provider name: `simulated`, `dhan` or `zerodha`.
* **Lists** are plain arrays with `limit` / `offset`; there is no total count yet.
* **`GET /market-data/instruments`** with an empty `search` returns the first `limit` instruments alphabetically.
* **Rejected orders**: `POST /orders` answers 400 with `data.order_id`; the rejected order is persisted and listed
  under `status_group=rejected`.
