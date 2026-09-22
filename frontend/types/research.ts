// Types for the AI-assisted research module, generated from docs/research_openapi.json.
//
// Notes on exactness:
// * Field names, enums and nullability mirror the OpenAPI schemas.
// * The OpenAPI marks response fields that have server-side defaults as "optional". The backend always serialises
//   them (verified against every file in docs/research_samples), so they are typed as present here. The one
//   exception is ResearchRunRead.agents, which the run list omits.
// * Request bodies (RunRequest, WeightSetCreate, SourceRegistryUpdate, UniverseWrite) keep their optional fields.
// * Confidence-like fields on agents, provenance, verification claims, sources and the market regime are 0..1;
//   research_score, data_confidence and coverage percentages are 0..100.

export type AgentStatus = "PENDING" | "RUNNING" | "SUCCESS" | "PARTIAL" | "FAILED" | "SKIPPED" | "NOT_AVAILABLE";
export type ClaimStatus = "VERIFIED" | "PARTIALLY_VERIFIED" | "CONFLICTING" | "UNVERIFIED" | "STALE";
export type ComponentRating = "EXCELLENT" | "GOOD" | "FAIR" | "POOR" | "UNAVAILABLE";
export type EmaStack = "BULLISH" | "BEARISH" | "MIXED" | "UNKNOWN";
export type GapDirection = "UP" | "DOWN" | "NONE";
export type MarketState = "OPEN" | "PRE_MARKET" | "POST_MARKET" | "CLOSED";
export type PriceStructure = "HIGHER_HIGHS_LOWS" | "LOWER_HIGHS_LOWS" | "MIXED" | "UNKNOWN";
export type PriceVolumeRelation =
  "PRICE_UP_VOLUME_UP" | "PRICE_UP_VOLUME_DOWN" | "PRICE_DOWN_VOLUME_UP" | "PRICE_DOWN_VOLUME_DOWN" | "UNKNOWN";
export type RegimeLabel = "STRONG_BULLISH" | "BULLISH" | "RANGE" | "BEARISH" | "STRONG_BEARISH" | "UNKNOWN";
export type ResearchDepth = "QUICK" | "STANDARD" | "DEEP";
export type ResearchDirection = "BULLISH" | "BEARISH" | "NEUTRAL";
export type ResearchSourceType =
  | "EXCHANGE"
  | "REGULATOR"
  | "COMPANY_FILING"
  | "NEWS_PROVIDER"
  | "FINANCIAL_PORTAL"
  | "MARKET_DATA_PROVIDER"
  | "SIMULATED"
  | "DERIVED"
  | "OTHER";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
export type SetupQuality = "STRONG" | "MODERATE" | "WEAK" | "UNKNOWN";
export type StretchState = "OVERBOUGHT" | "OVERSOLD";
export type Trend = "UP" | "DOWN" | "SIDEWAYS" | "UNKNOWN";
export type VolatilityState = "HIGH" | "NORMAL" | "LOW" | "UNKNOWN";
export type VwapEvent = "VWAP_RECLAIM" | "VWAP_REJECTION";
export type VwapPosition = "ABOVE" | "BELOW" | "AT";
export type WarningSeverity = "INFO" | "WARNING" | "HIGH";

export interface RunRequest {
  market?: "NSE";
  universe?: string;
  /** Required when universe is CUSTOM */
  symbols?: string[] | null;
  research_type?: "INTRADAY";
  depth?: ResearchDepth;
  /** Analyse the market as it was at this time. Defaults to now. */
  as_of?: string | null;
}

export interface ResearchRunRead {
  id: string;
  run_number: number;
  status: string;
  market: string;
  universe: string;
  research_type: string;
  depth: string;
  as_of: string;
  is_live: boolean;
  market_state: string | null;
  data_source: string | null;
  is_synthetic: boolean;
  weight_set_id: string | null;
  requested_symbols: string[] | null;
  candidates_scanned: number;
  candidates_analyzed: number;
  sources_checked: number;
  conflicts_found: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
  agents?: AgentRunRead[];
}

export interface AgentRunRead {
  agent: string;
  label: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  records: number;
  warnings: string[] | null;
  message: string | null;
}

export interface ResearchSummaryRead {
  latest_run: ResearchRunRead | null;
  active_run: ResearchRunRead | null;
}

export interface CandidateList {
  run: ResearchRunRead | null;
  items: CandidateRead[];
  sectors: string[];
  total: number;
}

export interface CandidateRead {
  rank: number | null;
  symbol: string;
  company: string;
  sector: string | null;
  stage: string;
  exclusion_reason: string | null;
  price: number | null;
  change_pct: number | null;
  rel_volume: number | null;
  atr_pct: number | null;
  vwap: number | null;
  vwap_position: string | null;
  research_score: number | null;
  data_confidence: number | null;
  coverage_pct: number | null;
  risk_level: string | null;
  direction: string | null;
  setup_quality: string | null;
  catalyst: string;
  initial_score: number | null;
  warning_count: number;
  reasons: string[];
  as_of: string | null;
  run_id: string;
}

export interface MarketOverview {
  run_id: string;
  run_number: number;
  generated_at: string;
  is_synthetic: boolean;
  data_source: string | null;
  context: MarketContext;
}

export interface MarketContext {
  as_of: string;
  market_state: MarketState;
  market_state_note: string;
  indices: IndexSnapshot[];
  india_vix: number | null;
  india_vix_change_pct: number | null;
  breadth: Breadth | null;
  regime: MarketRegime;
  sectors: SectorSnapshot[];
  unavailable: string[];
  provenance: Provenance;
}

export interface MarketRegime {
  label: RegimeLabel;
  volatility: VolatilityState;
  confidence: number;
  score: number;
  factors: RegimeFactor[];
}

export interface RegimeFactor {
  name: string;
  value: string;
  bullish: boolean | null;
  detail: string;
}

export interface IndexSnapshot {
  symbol: string;
  name: string;
  available: boolean;
  price: number | null;
  change_pct: number | null;
  ema20: number | null;
  ema50: number | null;
  trend: Trend;
  rsi: number | null;
  ret_5d_pct: number | null;
}

export interface Breadth {
  advances: number;
  declines: number;
  unchanged: number;
  universe_size: number;
  pct_above_vwap: number | null;
  pct_above_ema20: number | null;
  note: string;
}

export interface SectorOverview {
  run_id: string;
  run_number: number;
  as_of: string;
  is_synthetic: boolean;
  sectors: SectorSnapshot[];
}

export interface SectorSnapshot {
  sector: string;
  constituents: number;
  ret_1d_pct: number | null;
  ret_5d_pct: number | null;
  rel_strength_1d: number | null;
  rel_strength_5d: number | null;
  avg_rel_volume: number | null;
  breadth_pct: number | null;
  momentum: number | null;
  trend: Trend;
  rank: number | null;
}

export interface WeightSetRead {
  id: string;
  name: string;
  version: number;
  status: string;
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  notes: string | null;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface WeightSetCreate {
  name: string;
  weights: Record<string, number>;
  thresholds?: Record<string, number>;
  notes?: string | null;
}

export interface SourceRegistryRead {
  id: string;
  key: string;
  name: string;
  source_type: string;
  priority: number;
  base_url: string | null;
  enabled: boolean;
  connected: boolean;
  rate_limit_per_minute: number | null;
  reliability_score: number;
  notes: string | null;
}

export interface SourceRegistryUpdate {
  enabled?: boolean | null;
  reliability_score?: number | null;
  rate_limit_per_minute?: number | null;
  base_url?: string | null;
  notes?: string | null;
}

export interface UniverseRead {
  name: string;
  count: number;
  members: UniverseMemberRead[];
  note: string | null;
}

export interface UniverseMemberRead {
  symbol: string;
  sector: string | null;
  company: string | null;
}

export interface UniverseWrite {
  members: UniverseMemberWrite[];
}

export interface UniverseMemberWrite {
  symbol: string;
  sector?: string | null;
}

export interface ResearchReport {
  symbol: string;
  company: string;
  sector: string | null;
  run_id: string;
  generated_at: string;
  as_of: string;
  market_state: MarketState;
  data_source: string;
  is_synthetic: boolean;
  research_score: number | null;
  data_confidence: number;
  score_coverage_pct: number;
  direction: ResearchDirection;
  setup_quality: SetupQuality;
  risk_level: RiskLevel;
  labels: Record<string, string>;
  overview: ReportOverview;
  price: PriceBlock;
  volatility: VolatilityBlock;
  score: ScoreResult;
  technical: TechnicalAnalysis;
  historical: HistoricalAnalysis | null;
  risk: RiskAssessment;
  verification: VerificationReport;
  market_context: MarketContext;
  sector_context: SectorSnapshot | null;
  why_listed: string[];
  risks: string[];
  invalidation: string[];
  warnings: ResearchWarning[];
  sources: SourceRef[];
  agents: AgentTrace[];
  not_assessed: string[];
  disclaimer: string;
}

export interface ReportOverview {
  price: number;
  change: number | null;
  change_pct: number | null;
  volume: number;
  avg_volume: number | null;
  market_cap: number | null;
  sector: string | null;
  industry: string | null;
  exchange: string;
}

export interface PriceBlock {
  price: number;
  prev_close: number | null;
  day_open: number;
  day_high: number;
  day_low: number;
  change: number | null;
  change_pct: number | null;
  gap_pct: number | null;
  ret_5d_pct: number | null;
  ret_20d_pct: number | null;
  volume: number;
  avg_volume: number | null;
  rel_volume: number | null;
  volume_spike: boolean;
  avg_traded_value_cr: number | null;
  session_date: string;
  bars_in_session: number;
  last_bar_time: string;
  bid: number | null;
  ask: number | null;
  spread_bps: number | null;
}

export interface VolatilityBlock {
  atr: number | null;
  atr_pct: number | null;
  hist_vol_pct: number | null;
  intraday_range_pct: number | null;
  avg_daily_range_pct: number | null;
  bb_width_pct: number | null;
}

export interface ResearchWarning {
  code: string;
  severity: WarningSeverity;
  message: string;
  symbol: string | null;
}

export interface ScoreResult {
  research_score: number | null;
  raw_score: number | null;
  capped: boolean;
  cap_reason: string | null;
  available_points: number;
  total_points: number;
  coverage_pct: number;
  components: ScoreComponent[];
  weight_set_id: string | null;
  weight_set_version: number | null;
  setup_quality: SetupQuality;
  direction: ResearchDirection;
}

export interface ScoreComponent {
  key: string;
  label: string;
  points: number;
  max_points: number;
  available: boolean;
  rating: ComponentRating;
  summary: string;
  evidence: EvidenceItem[];
  metrics: Record<string, unknown>;
  sources: string[];
}

export interface EvidenceItem {
  label: string;
  value: string;
  passed: boolean | null;
  source_key: string | null;
}

export interface ComponentChange {
  key: string;
  label: string;
  from_points: number;
  to_points: number;
  delta: number;
}

export interface ScoreChange {
  from_run_id: string;
  to_run_id: string;
  from_as_of: string;
  to_as_of: string;
  from_score: number | null;
  to_score: number | null;
  delta: number | null;
  reasons: string[];
  component_changes: ComponentChange[];
}

export interface ScorePoint {
  run_id: string;
  as_of: string;
  research_score: number | null;
  data_confidence: number;
  direction: string;
  risk_level: string;
}

export interface ScoreHistory {
  symbol: string;
  points: ScorePoint[];
  changes: ScoreChange[];
}

export interface ReportSummary {
  run_id: string;
  run_number: number | null;
  as_of: string;
  research_score: number | null;
  data_confidence: number;
  direction: string;
  setup_quality: string;
  risk_level: string;
  rank: number | null;
  is_synthetic: boolean;
}

export interface TechnicalAnalysis {
  timeframes: TimeframeTechnical[];
  price_action: PriceAction;
  levels: IntradayLevels;
  direction: ResearchDirection;
  direction_votes: EvidenceItem[];
  provenance: Provenance;
}

export interface TimeframeTechnical {
  timeframe: string;
  bars: number;
  ema9: number | null;
  ema20: number | null;
  ema50: number | null;
  ema100: number | null;
  ema200: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  roc: number | null;
  adx: number | null;
  plus_di: number | null;
  minus_di: number | null;
  atr: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_width_pct: number | null;
  supertrend: number | null;
  supertrend_dir: number | null;
  volume_ma: number | null;
  rel_volume: number | null;
  trend: Trend;
  ema_stack: EmaStack;
}

export interface PriceAction {
  structure: PriceStructure;
  swing_highs: number;
  swing_lows: number;
  breakout: "UP" | "DOWN" | null;
  breakout_level: number | null;
  breakout_20d: "UP" | "DOWN" | null;
  consolidation: boolean;
  range_expansion: boolean;
  stretched: StretchState | null;
  vwap_event: VwapEvent | null;
  price_volume: PriceVolumeRelation;
  tags: string[];
}

export interface IntradayLevels {
  vwap: number | null;
  vwap_position: VwapPosition | null;
  vwap_distance_pct: number | null;
  opening_range_15_high: number | null;
  opening_range_15_low: number | null;
  opening_range_30_high: number | null;
  opening_range_30_low: number | null;
  prev_day_high: number | null;
  prev_day_low: number | null;
  prev_day_close: number | null;
  gap_pct: number | null;
  gap_direction: GapDirection;
  gap_filled_today: boolean | null;
  support: number[];
  resistance: number[];
}

export interface HistoricalAnalysis {
  sessions_analyzed: number;
  period_start: string | null;
  period_end: string | null;
  current_setup_key: string | null;
  current_setup_label: string | null;
  matched: PatternStat | null;
  setups: PatternStat[];
  baseline_moves: Record<string, number>;
  estimated_round_trip_cost_pct: number;
  warnings: string[];
  provenance: Provenance;
}

export interface PatternStat {
  key: string;
  label: string;
  description: string;
  horizon: string;
  occurrences: number;
  successful: number | null;
  success_rate: number | null;
  avg_return_pct: number | null;
  median_return_pct: number | null;
  avg_return_net_pct: number | null;
  mfe_pct: number | null;
  mae_pct: number | null;
  horizon_returns_pct: Record<string, number>;
  reach_probability: Record<string, number>;
  sample_adequate: boolean;
  min_sample: number;
  period_start: string | null;
  period_end: string | null;
  note: string | null;
}

export interface RiskAssessment {
  flags: RiskFlag[];
  liquidity_risk: RiskLevel;
  volatility_risk: RiskLevel;
  event_risk: RiskLevel;
  corporate_risk: RiskLevel;
  data_risk: RiskLevel;
  market_risk: RiskLevel;
  overall: RiskLevel;
  unavailable_checks: string[];
  provenance: Provenance;
}

export interface RiskFlag {
  code: string;
  severity: WarningSeverity;
  message: string;
  metric: string | null;
  value: number | null;
}

export interface VerificationReport {
  claims: VerificationClaim[];
  conflicts_found: number;
  sources_checked: number;
  data_confidence: number;
  breakdown: ConfidenceBreakdown;
  provenance: Provenance;
}

export interface VerificationClaim {
  key: string;
  claim: string;
  status: ClaimStatus;
  confidence: number;
  sources_checked: number;
  independent_origins: number;
  values: SourceValue[];
  tolerance_pct: number | null;
  detail: string;
  resolution: string | null;
}

export interface SourceValue {
  source: string;
  origin: string;
  value: number | string | boolean;
  data_as_of: string | null;
  reliability: number;
}

export interface ConfidenceBreakdown {
  source_reliability: number;
  freshness: number;
  verification: number;
  completeness: number;
  sample_adequacy: number;
  synthetic_cap_applied: boolean;
}

export interface SourceRef {
  key: string;
  name: string;
  source_type: ResearchSourceType;
  tier: number;
  reliability: number;
  origin: string;
  retrieved_at: string | null;
  data_as_of: string | null;
  url: string | null;
  note: string | null;
}

export interface Provenance {
  source: string;
  source_type: ResearchSourceType;
  data_as_of: string | null;
  retrieved_at: string;
  confidence: number;
  stale: boolean;
  note: string | null;
}

export interface AgentTrace {
  agent: string;
  label: string;
  status: AgentStatus;
  confidence: number | null;
  timestamp: string | null;
  duration_ms: number | null;
  summary: string;
  findings: string[];
  warnings: string[];
}

export interface TechnicalView {
  symbol: string;
  run_id: string;
  as_of: string;
  price: PriceBlock;
  volatility: VolatilityBlock;
  technical: TechnicalAnalysis;
  levels: IntradayLevels;
}

export interface RiskView {
  symbol: string;
  run_id: string;
  as_of: string;
  risk: RiskAssessment;
  warnings: ResearchWarning[];
}

export interface SourcesView {
  symbol: string;
  run_id: string;
  sources: SourceRef[];
  claims: VerificationClaim[];
  data_confidence: number;
  provenance: Provenance[];
}

export type WeightKey =
  | "market_regime"
  | "liquidity"
  | "price_action"
  | "momentum"
  | "volume"
  | "volatility"
  | "technical_setup"
  | "news_catalyst"
  | "historical_setup"
  | "risk";

export type ResearchSortKey = "score" | "confidence" | "rel_volume" | "change" | "atr" | "price" | "symbol" | "initial";

export interface CandidatesQuery {
  run_id?: string;
  min_score?: number;
  min_confidence?: number;
  min_rel_volume?: number;
  sector?: string;
  risk?: "LOW" | "MEDIUM" | "HIGH";
  direction?: ResearchDirection;
  min_price?: number;
  max_price?: number;
  sort?: ResearchSortKey;
  order?: "desc" | "asc";
  include_unanalyzed?: boolean;
  limit?: number;
}
