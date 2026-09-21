// TypeScript types mirroring docs/API_CONTRACT.md (v1) exactly.
// All JSON is snake_case. Timestamps are ISO-8601 UTC strings, dates are YYYY-MM-DD.
// Config values such as risk_per_trade are fractions (0.01 = 1%).
// Metrics named *_pct / win_rate are percent numbers (71.4 = 71.4%).

export type ISODateTime = string;
export type ISODate = string;

// ---------- Envelope ----------
export interface ApiStatus {
  code: number;
  description: string;
}
export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  status: ApiStatus;
  data: T;
}
export interface ValidationErrorItem {
  field: string;
  message: string;
}

// ---------- Shared enums ----------
export type TradingMode = "BACKTEST" | "PAPER" | "SANDBOX" | "LIVE";
export type SystemState = "RUNNING" | "HALTED";
export type MarketDataProvider = "simulated" | "dhan" | "zerodha";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "1d";
export type PositionSide = "LONG" | "SHORT";
export type OrderSide = "BUY" | "SELL";

// ---------- Auth ----------
export interface AuthStatus {
  auth_enabled: boolean;
  registration_open: boolean;
  has_users: boolean;
}
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: ISODateTime;
}
export interface AuthToken {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}
export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}
export interface LoginRequest {
  email: string;
  password: string;
}

// ---------- System ----------
export interface Health {
  status: "ok";
  database: "ok" | "error";
  trading_mode: TradingMode;
  live_trading_enabled: boolean;
}
export type ComponentKey =
  | "broker"
  | "market_data"
  | "strategy_engine"
  | "order_engine"
  | "database"
  | "redis";
export type ComponentStatus =
  | "CONNECTED"
  | "DISCONNECTED"
  | "RUNNING"
  | "STOPPED"
  | "HALTED"
  | "NOT_CONFIGURED"
  | "DEGRADED";
export interface SystemComponent {
  key: ComponentKey;
  name: string;
  status: ComponentStatus;
  detail: string | null;
}
export interface SystemStatus {
  trading_mode: TradingMode;
  live_trading_enabled: boolean;
  kill_switch_active: boolean;
  system_state: SystemState;
  market_data_provider: MarketDataProvider;
  server_time: ISODateTime;
  components: SystemComponent[];
}
export interface ChargesConfig {
  brokerage_per_order: number;
  brokerage_pct: number;
  stt_sell_pct: number;
  exchange_txn_pct: number;
  sebi_pct: number;
  stamp_duty_buy_pct: number;
  gst_pct: number;
}
export interface SystemConfig {
  app_name: string;
  app_env: string;
  version: string;
  trading_mode: TradingMode;
  live_trading_enabled: boolean;
  auth_enabled: boolean;
  workers_enabled: boolean;
  market_data_provider: MarketDataProvider;
  paper_initial_capital: number;
  paper_slippage_pct: number;
  strategy_poll_seconds: number;
  order_monitor_poll_seconds: number;
  market_data_poll_seconds: number;
  default_charges: ChargesConfig;
  brokers_configured: { DHAN: boolean; ZERODHA: boolean; FYERS: boolean };
}
export type EventLevel = "INFO" | "WARNING" | "ERROR";
export const EVENT_TYPES = [
  "strategy_started",
  "strategy_stopped",
  "signal_generated",
  "risk_check_passed",
  "risk_check_failed",
  "order_submitted",
  "order_filled",
  "order_partially_filled",
  "order_rejected",
  "order_cancelled",
  "order_failed",
  "position_opened",
  "position_closed",
  "broker_connected",
  "broker_disconnected",
  "kill_switch_activated",
  "kill_switch_deactivated",
  "backtest_completed",
] as const;
export interface SystemEvent {
  id: string;
  event_type: string;
  level: EventLevel;
  message: string;
  payload: Record<string, unknown> | null;
  strategy_id: string | null;
  order_id: string | null;
  symbol: string | null;
  created_at: ISODateTime;
}
export interface EventsQuery {
  limit?: number;
  offset?: number;
  event_type?: string;
  level?: EventLevel;
  strategy_id?: string;
}

// ---------- Dashboard ----------
export interface DashboardSummary {
  capital: number;
  available: number;
  used_margin: number;
  todays_pnl: number;
  realized_pnl_today: number;
  open_pnl: number;
  total_pnl: number;
  win_rate: number;
  trades_today: number;
  open_positions: number;
  running_strategies: number;
  trading_mode: TradingMode;
  currency: "INR";
}
export interface DailyPnl {
  date: ISODate;
  realized_pnl: number;
  unrealized_pnl: number;
  charges: number;
  net_pnl: number;
  trades: number;
  wins: number;
  losses: number;
}
export interface EquityPoint {
  timestamp: ISODateTime;
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
}
export interface DashboardPnl {
  daily: DailyPnl[];
  equity_curve: EquityPoint[];
}
export interface StrategyPerformance {
  strategy_id: string;
  strategy_name: string;
  trades: number;
  win_rate: number;
  net_pnl: number;
}
export interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  profit_factor: number | null;
  average_trade: number;
  largest_win: number;
  largest_loss: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  total_charges: number;
  by_strategy: StrategyPerformance[];
}

// ---------- Brokers ----------
export type BrokerType = "PAPER" | "DHAN" | "ZERODHA" | "FYERS";
export type BrokerEnvironment = "PAPER" | "SANDBOX" | "LIVE";
export type BrokerConnectionStatus =
  | "CONNECTED"
  | "DISCONNECTED"
  | "NOT_CONFIGURED"
  | "UNKNOWN";
export interface BrokerAccount {
  id: string;
  name: string;
  broker_type: BrokerType;
  environment: BrokerEnvironment;
  is_active: boolean;
  is_default: boolean;
  credentials_configured: boolean;
  connection_status: BrokerConnectionStatus;
  last_checked_at: ISODateTime | null;
  last_error: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export interface BrokerAccountCreate {
  name: string;
  broker_type: BrokerType;
  environment: BrokerEnvironment;
  is_default?: boolean;
}
export interface BrokerAccountUpdate {
  name?: string;
  is_active?: boolean;
  is_default?: boolean;
}
export interface LiveGuard {
  name: string;
  passed: boolean;
  detail: string;
}
export interface SupportedBroker {
  broker_type: BrokerType;
  implemented: boolean;
  credentials_configured: boolean;
  environments: string[];
}
export interface BrokerStatus {
  trading_mode: TradingMode;
  live_trading_enabled: boolean;
  live_guards: LiveGuard[];
  order_routing: string;
  supported: SupportedBroker[];
}
export interface BrokerTestResult {
  broker_account_id: string;
  broker_type: BrokerType;
  connected: boolean;
  latency_ms: number | null;
  detail: string;
}

// ---------- Strategies ----------
export type StrategyType = "EMA_CROSSOVER" | "VWAP" | "BREAKOUT";
export type StrategyStatus = "STOPPED" | "RUNNING" | "ERROR";
export interface StrategyParameterInfo {
  key: string;
  label: string;
  type: "int" | "float";
  default: number;
  min: number;
  max: number;
  description: string;
}
export interface StrategyTypeInfo {
  type: StrategyType;
  name: string;
  description: string;
  parameters: StrategyParameterInfo[];
}
export interface StrategyCreate {
  name: string;
  strategy_type: StrategyType;
  symbol: string;
  exchange?: string;
  timeframe: Timeframe;
  capital: number;
  risk_per_trade: number;
  stop_loss_pct: number;
  target_pct: number | null;
  allow_short?: boolean;
  trading_mode?: TradingMode;
  broker_account_id: string | null;
  parameters: Record<string, number>;
}
export type StrategyUpdate = Partial<StrategyCreate>;
export interface StrategyStats {
  todays_pnl: number;
  total_pnl: number;
  trades: number;
  win_rate: number;
  open_position_qty: number;
}
export interface Strategy extends Required<StrategyCreate> {
  id: string;
  status: StrategyStatus;
  broker_name: string | null;
  last_signal_at: ISODateTime | null;
  last_evaluated_at: ISODateTime | null;
  last_error: string | null;
  stats: StrategyStats;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
export type SignalType = "BUY" | "SELL" | "HOLD";
export type SignalStatus = "GENERATED" | "EXECUTED" | "REJECTED" | "IGNORED";
export interface Signal {
  id: string;
  strategy_id: string;
  strategy_name: string;
  symbol: string;
  exchange: string;
  signal_type: SignalType;
  price: number;
  reason: string;
  indicators: Record<string, unknown>;
  status: SignalStatus;
  status_reason: string | null;
  order_id: string | null;
  candle_time: ISODateTime;
  created_at: ISODateTime;
}

// ---------- Orders ----------
export type OrderType = "MARKET" | "LIMIT" | "SL" | "SL-M";
export type ProductType = "INTRADAY" | "DELIVERY";
export type OrderStatus =
  | "CREATED"
  | "SUBMITTED"
  | "OPEN"
  | "TRIGGER_PENDING"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCELLED"
  | "REJECTED"
  | "FAILED"
  | "EXPIRED";
export type OrderSource = "MANUAL" | "STRATEGY" | "RISK_EXIT" | "KILL_SWITCH";
export type OrderStatusGroup = "all" | "open" | "filled" | "rejected" | "cancelled";
export const OPEN_ORDER_STATUSES: readonly OrderStatus[] = [
  "CREATED",
  "SUBMITTED",
  "OPEN",
  "TRIGGER_PENDING",
  "PARTIALLY_FILLED",
];
export interface OrderCreate {
  symbol: string;
  exchange?: string;
  side: OrderSide;
  order_type: OrderType;
  product_type?: ProductType;
  quantity: number;
  price?: number;
  trigger_price?: number;
  stop_loss?: number;
  target?: number;
}
export interface OrderUpdate {
  quantity?: number;
  price?: number;
  trigger_price?: number;
}
export interface OrderEvent {
  id: string;
  order_id: string;
  event_type: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus | null;
  message: string | null;
  payload: Record<string, unknown> | null;
  created_at: ISODateTime;
}
export interface Order {
  id: string;
  broker_order_id: string | null;
  broker_account_id: string | null;
  broker_type: BrokerType | null;
  strategy_id: string | null;
  strategy_name: string | null;
  symbol: string;
  exchange: string;
  side: OrderSide;
  order_type: OrderType;
  product_type: ProductType;
  quantity: number;
  filled_quantity: number;
  pending_quantity: number;
  price: number | null;
  trigger_price: number | null;
  average_fill_price: number | null;
  stop_loss: number | null;
  target: number | null;
  status: OrderStatus;
  status_message: string | null;
  trading_mode: TradingMode;
  source: OrderSource;
  retry_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  events?: OrderEvent[];
}
export interface OrdersQuery {
  status_group?: OrderStatusGroup;
  symbol?: string;
  strategy_id?: string;
  limit?: number;
  offset?: number;
}

// ---------- Positions ----------
export type PositionStatus = "OPEN" | "CLOSED";
export type PositionStatusFilter = "open" | "closed" | "all";
export interface Position {
  id: string;
  symbol: string;
  exchange: string;
  strategy_id: string | null;
  strategy_name: string | null;
  side: PositionSide;
  quantity: number;
  average_entry_price: number;
  last_price: number | null;
  unrealized_pnl: number;
  realized_pnl: number;
  stop_loss: number | null;
  target: number | null;
  status: PositionStatus;
  trading_mode: TradingMode;
  opened_at: ISODateTime;
  closed_at: ISODateTime | null;
  updated_at: ISODateTime;
}
export interface PositionUpdate {
  stop_loss?: number | null;
  target?: number | null;
}

// ---------- Trades ----------
export type ExitReason = "SIGNAL" | "STOP_LOSS" | "TARGET" | "MANUAL" | "KILL_SWITCH";
export interface Trade {
  id: string;
  position_id: string;
  strategy_id: string | null;
  strategy_name: string | null;
  symbol: string;
  exchange: string;
  side: PositionSide;
  quantity: number;
  entry_price: number;
  exit_price: number;
  entry_time: ISODateTime;
  exit_time: ISODateTime;
  gross_pnl: number;
  charges: number;
  net_pnl: number;
  exit_reason: ExitReason;
  trading_mode: TradingMode;
  created_at: ISODateTime;
}
export interface TradesQuery {
  strategy_id?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
}

// ---------- Backtests ----------
export type BacktestStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
export interface BacktestCreate {
  name?: string;
  strategy_id?: string;
  strategy_type?: StrategyType;
  parameters?: Record<string, number>;
  symbol?: string;
  exchange?: string;
  timeframe?: Timeframe;
  risk_per_trade?: number;
  stop_loss_pct?: number;
  target_pct?: number | null;
  allow_short?: boolean;
  start_date: ISODate;
  end_date: ISODate;
  initial_capital: number;
  brokerage_per_order?: number;
  brokerage_pct?: number;
  slippage_pct?: number;
  include_statutory_charges?: boolean;
}
export interface BacktestConfig {
  risk_per_trade: number;
  stop_loss_pct: number;
  target_pct: number | null;
  allow_short: boolean;
  slippage_pct: number;
  charges: ChargesConfig;
}
export interface BacktestMetrics {
  final_capital: number;
  net_pnl: number;
  total_return_pct: number;
  gross_profit: number;
  gross_loss: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number | null;
  max_drawdown: number;
  max_drawdown_pct: number;
  average_trade: number;
  largest_win: number;
  largest_loss: number;
  sharpe_ratio: number | null;
  total_charges: number;
  total_slippage: number;
  candles_processed: number;
  data_source: string;
}
export interface Backtest {
  id: string;
  name: string;
  strategy_id: string | null;
  strategy_type: StrategyType;
  parameters: Record<string, number>;
  symbol: string;
  exchange: string;
  timeframe: Timeframe;
  start_date: ISODate;
  end_date: ISODate;
  status: BacktestStatus;
  error_message: string | null;
  initial_capital: number;
  config: BacktestConfig;
  metrics: BacktestMetrics | null;
  created_at: ISODateTime;
  completed_at: ISODateTime | null;
}
export interface BacktestTrade {
  id: string;
  entry_time: ISODateTime;
  exit_time: ISODateTime;
  symbol: string;
  side: PositionSide;
  entry_price: number;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  charges: number;
  net_pnl: number;
  exit_reason: string;
}
export interface BacktestEquityPoint {
  timestamp: ISODateTime;
  equity: number;
  drawdown: number;
  drawdown_pct: number;
}
export interface MonthlyReturn {
  month: string;
  net_pnl: number;
  trades: number;
}
export interface BacktestReport {
  backtest: Backtest;
  trades: BacktestTrade[];
  equity_curve: BacktestEquityPoint[];
  monthly_returns: MonthlyReturn[];
}

// ---------- Risk ----------
export interface RiskLimits {
  max_risk_per_trade: number;
  max_daily_loss: number;
  max_trades_per_day: number;
  max_open_positions: number;
  max_position_size: number;
  max_order_value: number;
  max_consecutive_losses: number;
  max_strategy_drawdown: number;
  close_positions_on_kill_switch: boolean;
}
export interface RiskConfiguration extends RiskLimits {
  id: string;
  kill_switch_active: boolean;
  kill_switch_activated_at: ISODateTime | null;
  kill_switch_reason: string | null;
  updated_at: ISODateTime;
}
export type RiskConfigurationUpdate = Partial<RiskLimits>;
export interface RiskUsage {
  key: string;
  label: string;
  current: number;
  limit: number;
  utilization: number;
  breached: boolean;
  unit: "INR" | "count";
}
export interface RiskStatus {
  kill_switch_active: boolean;
  system_state: SystemState;
  trading_allowed: boolean;
  blocked_reasons: string[];
  usage: RiskUsage[];
}
export interface KillSwitchRequest {
  activate: boolean;
  confirm: true;
  reason?: string;
}
export interface KillSwitchResult {
  kill_switch_active: boolean;
  strategies_stopped: number;
  orders_cancelled: number;
  positions_closed: number;
  message: string;
}

// ---------- Market data ----------
export interface Instrument {
  id: string;
  symbol: string;
  exchange: string;
  name: string;
  segment: string;
  exchange_token: string | null;
  lot_size: number;
  tick_size: number;
  is_active: boolean;
}
export interface InstrumentCreate {
  symbol: string;
  exchange: string;
  name: string;
  exchange_token?: string;
  lot_size?: number;
  tick_size?: number;
}
export interface Quote {
  symbol: string;
  exchange: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: ISODateTime;
  source: string;
}
export interface Candle {
  timestamp: ISODateTime;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
export interface CandlesQuery {
  symbol: string;
  exchange?: string;
  timeframe?: Timeframe;
  start?: string;
  end?: string;
  limit?: number;
}
export interface HistoricalSyncRequest {
  symbol: string;
  exchange: string;
  timeframe: Timeframe;
  start_date: ISODate;
  end_date: ISODate;
}
export interface HistoricalSyncResult {
  stored: number;
  total: number;
  source: string;
}
