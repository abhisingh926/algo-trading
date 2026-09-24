"""Typed contracts shared by the research agents, the API and the database JSON columns.

Agents never pass free text to each other: every hand-off is one of these Pydantic models.
Statuses use Literal strings so they serialise as plain JSON.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MarketState = Literal["OPEN", "PRE_MARKET", "POST_MARKET", "CLOSED"]
Direction = Literal["BULLISH", "BEARISH", "NEUTRAL"]
Severity = Literal["INFO", "WARNING", "HIGH"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
Rating = Literal["EXCELLENT", "GOOD", "FAIR", "POOR", "UNAVAILABLE"]
AgentStatus = Literal["PENDING", "RUNNING", "SUCCESS", "PARTIAL", "FAILED", "SKIPPED", "NOT_AVAILABLE"]
VerificationStatus = Literal["VERIFIED", "PARTIALLY_VERIFIED", "CONFLICTING", "UNVERIFIED", "STALE"]
SourceType = Literal[
    "EXCHANGE",
    "REGULATOR",
    "COMPANY_FILING",
    "NEWS_PROVIDER",
    "FINANCIAL_PORTAL",
    "MARKET_DATA_PROVIDER",
    "SIMULATED",
    "DERIVED",
    "OTHER",
]

AGENT_LABELS: dict[str, str] = {
    "MarketScannerAgent": "Market Scanner",
    "MarketResearchAgent": "Data Research",
    "DataVerificationAgent": "Data Verification",
    "HistoricalTechnicalAgent": "Historical & Technical Analysis",
    "FundamentalResearchAgent": "Fundamental Analysis",
    "NewsCatalystAgent": "News & Catalyst Analysis",
    "MarketRiskAgent": "Market & Risk Analysis",
    "QuantScoringAgent": "Quant Scoring",
    "ResearchSynthesizerAgent": "Research Synthesis",
    "ResearchQualityAgent": "Research Quality Check",
}
# Agents that do not exist yet. They are listed in every run so the UI is honest about what was NOT analysed.
UNAVAILABLE_AGENTS: dict[str, str] = {
    "MarketResearchAgent": "Company data, announcements and corporate events need a licensed or permitted data source (planned phase 2).",
    "NewsCatalystAgent": "News analysis needs a news source and an LLM key (planned phase 2).",
    "FundamentalResearchAgent": "Fundamentals need a data vendor subscription (planned phase 3).",
}

DISCLAIMER = (
    "Research and decision support only. This is not investment advice or a recommendation to buy or sell. "
    "Scores describe how a setup measures up against explicit rules on the data available at the time, "
    "and have not been shown to predict profit."
)


Freshness = Literal["LIVE", "RECENT", "STALE", "UNKNOWN"]


class Provenance(BaseModel):
    source: str
    source_type: SourceType
    data_as_of: datetime | None = None
    retrieved_at: datetime
    confidence: float = Field(ge=0, le=1)
    stale: bool = False
    freshness: Freshness = "UNKNOWN"  # stale data must never look the same as live data
    age_minutes: float | None = None
    note: str | None = None


class SourceRef(BaseModel):
    key: str
    name: str
    source_type: SourceType
    tier: int = 3
    reliability: float = Field(ge=0, le=1)
    origin: str  # who actually produced the data; two keys with one origin are not independent
    retrieved_at: datetime | None = None
    data_as_of: datetime | None = None
    url: str | None = None
    note: str | None = None


class ResearchWarning(BaseModel):
    code: str
    severity: Severity
    message: str
    symbol: str | None = None


class EvidenceItem(BaseModel):
    label: str
    value: str
    passed: bool | None = None  # True renders a tick, False a cross, None neutral
    source_key: str | None = None


# ---- scanner -----------------------------------------------------------------------------------------------
class ScannerCandidate(BaseModel):
    symbol: str
    company: str
    sector: str | None = None
    stage: Literal["SCANNED", "SELECTED", "ANALYZED", "EXCLUDED"] = "SCANNED"
    exclusion_reason: str | None = None
    initial_score: float = 0.0  # the scanner's rough ranking only; it is NOT the research score
    reasons: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    price: float | None = None
    change_pct: float | None = None
    rel_volume: float | None = None
    atr_pct: float | None = None
    vwap: float | None = None
    vwap_position: str | None = None
    direction: Direction | None = None


# ---- agent envelope (the generic output every agent returns) ---------------------------------------------
class AgentOutput(BaseModel):
    agent: str
    symbol: str | None = None
    status: AgentStatus
    confidence: float = Field(default=0.0, ge=0, le=1)
    timestamp: datetime
    duration_ms: int = 0
    findings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---- price, volume, volatility ---------------------------------------------------------------------------
class PriceBlock(BaseModel):
    price: float
    prev_close: float | None = None
    day_open: float
    day_high: float
    day_low: float
    change: float | None = None
    change_pct: float | None = None
    gap_pct: float | None = None
    ret_5d_pct: float | None = None
    ret_20d_pct: float | None = None
    volume: int
    avg_volume: float | None = None
    rel_volume: float | None = None  # today's volume so far vs the average at the same time of day
    volume_spike: bool = False
    avg_traded_value_cr: float | None = None  # 20-session average traded value in INR crore
    session_date: str
    bars_in_session: int
    last_bar_time: datetime
    bid: float | None = None
    ask: float | None = None
    spread_bps: float | None = None


class VolatilityBlock(BaseModel):
    atr: float | None = None
    atr_pct: float | None = None
    hist_vol_pct: float | None = None
    intraday_range_pct: float | None = None
    avg_daily_range_pct: float | None = None
    bb_width_pct: float | None = None


class TimeframeTechnical(BaseModel):
    timeframe: str
    bars: int
    ema9: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    ema100: float | None = None
    ema200: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    roc: float | None = None
    adx: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    atr: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    bb_width_pct: float | None = None
    supertrend: float | None = None
    supertrend_dir: int | None = None
    volume_ma: float | None = None
    rel_volume: float | None = None
    trend: Literal["UP", "DOWN", "SIDEWAYS", "UNKNOWN"] = "UNKNOWN"
    ema_stack: Literal["BULLISH", "BEARISH", "MIXED", "UNKNOWN"] = "UNKNOWN"


class PriceAction(BaseModel):
    structure: Literal["HIGHER_HIGHS_LOWS", "LOWER_HIGHS_LOWS", "MIXED", "UNKNOWN"] = "UNKNOWN"
    swing_highs: int = 0
    swing_lows: int = 0
    breakout: Literal["UP", "DOWN"] | None = None
    breakout_level: float | None = None
    breakout_20d: Literal["UP", "DOWN"] | None = None
    consolidation: bool = False
    range_expansion: bool = False
    stretched: Literal["OVERBOUGHT", "OVERSOLD"] | None = None
    vwap_event: Literal["VWAP_RECLAIM", "VWAP_REJECTION"] | None = None
    price_volume: Literal[
        "PRICE_UP_VOLUME_UP",
        "PRICE_UP_VOLUME_DOWN",
        "PRICE_DOWN_VOLUME_UP",
        "PRICE_DOWN_VOLUME_DOWN",
        "UNKNOWN",
    ] = "UNKNOWN"
    tags: list[str] = Field(default_factory=list)


class IntradayLevels(BaseModel):
    vwap: float | None = None
    vwap_position: Literal["ABOVE", "BELOW", "AT"] | None = None
    vwap_distance_pct: float | None = None
    opening_range_15_high: float | None = None
    opening_range_15_low: float | None = None
    opening_range_30_high: float | None = None
    opening_range_30_low: float | None = None
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    prev_day_close: float | None = None
    gap_pct: float | None = None
    gap_direction: Literal["UP", "DOWN", "NONE"] = "NONE"
    gap_filled_today: bool | None = None
    support: list[float] = Field(default_factory=list)
    resistance: list[float] = Field(default_factory=list)


class TechnicalAnalysis(BaseModel):
    timeframes: list[TimeframeTechnical]
    price_action: PriceAction
    levels: IntradayLevels
    direction: Direction
    direction_votes: list[EvidenceItem]
    provenance: Provenance


# ---- historical behaviour ---------------------------------------------------------------------------------
class PatternStat(BaseModel):
    key: str
    label: str
    description: str
    horizon: str
    occurrences: int
    successful: int | None = None
    success_rate: float | None = None  # percent; None when the sample is too small to state one
    avg_return_pct: float | None = None
    median_return_pct: float | None = None
    avg_return_net_pct: float | None = None  # after the estimated round-trip trading cost
    mfe_pct: float | None = None  # average maximum favourable excursion
    mae_pct: float | None = None  # average maximum adverse excursion
    horizon_returns_pct: dict[str, float] = Field(
        default_factory=dict
    )  # average aligned return at 15m / 30m / 1h
    reach_probability: dict[str, float] = Field(
        default_factory=dict
    )  # "0.5" -> percent chance of reaching +0.5%
    sample_adequate: bool
    min_sample: int
    period_start: str | None = None
    period_end: str | None = None
    note: str | None = None


class HistoricalAnalysis(BaseModel):
    sessions_analyzed: int
    period_start: str | None
    period_end: str | None
    current_setup_key: str | None = None
    current_setup_label: str | None = None
    matched: PatternStat | None = (
        None  # the best-supported stat for today's setup (None if no adequate sample)
    )
    setups: list[PatternStat]
    baseline_moves: dict[str, float] = Field(
        default_factory=dict
    )  # average absolute move per horizon, percent
    estimated_round_trip_cost_pct: float
    warnings: list[str] = Field(default_factory=list)
    provenance: Provenance


# ---- risk --------------------------------------------------------------------------------------------------
class RiskFlag(BaseModel):
    code: str
    severity: Severity
    message: str
    metric: str | None = None
    value: float | None = None


class RiskComponent(BaseModel):
    """One measured dimension of risk. `score` runs 0 (no concern) to 100 (severe); None means not assessed."""

    key: str
    label: str
    score: float | None
    level: RiskLevel
    weight: float
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    # Headline: 0 = no measured concern, 100 = severe. HIGHER MEANS MORE RISK.
    risk_score: float | None
    risk_direction: str = "Higher means more risk (0 to 100)."
    coverage_pct: float = 0.0  # share of the risk weights that could actually be assessed
    components: list[RiskComponent] = Field(default_factory=list)
    flags: list[RiskFlag]
    liquidity_risk: RiskLevel
    volatility_risk: RiskLevel
    activity_risk: RiskLevel = "UNKNOWN"
    event_risk: RiskLevel = "UNKNOWN"
    corporate_risk: RiskLevel = "UNKNOWN"
    data_risk: RiskLevel
    market_risk: RiskLevel
    overall: RiskLevel
    unavailable_checks: list[str]
    provenance: Provenance


# ---- market and sector context --------------------------------------------------------------------------
class IndexSnapshot(BaseModel):
    symbol: str
    name: str
    available: bool
    price: float | None = None
    change_pct: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    trend: Literal["UP", "DOWN", "SIDEWAYS", "UNKNOWN"] = "UNKNOWN"
    rsi: float | None = None
    ret_5d_pct: float | None = None


class RegimeFactor(BaseModel):
    name: str
    value: str
    bullish: bool | None  # None when the factor is neutral or unavailable
    detail: str


class MarketRegime(BaseModel):
    label: Literal["STRONG_BULLISH", "BULLISH", "RANGE", "BEARISH", "STRONG_BEARISH", "UNKNOWN"]
    volatility: Literal["HIGH", "NORMAL", "LOW", "UNKNOWN"]
    confidence: float = Field(ge=0, le=1)
    score: float  # net of the bullish and bearish factors, -1..+1
    factors: list[RegimeFactor]


class Breadth(BaseModel):
    advances: int
    declines: int
    unchanged: int
    universe_size: int
    pct_above_vwap: float | None = None
    pct_above_ema20: float | None = None
    note: str = "Computed over the scanned universe, not the whole exchange."


class SectorSnapshot(BaseModel):
    sector: str
    constituents: int
    ret_1d_pct: float | None = None
    ret_5d_pct: float | None = None
    rel_strength_1d: float | None = None  # sector return minus NIFTY return, percentage points
    rel_strength_5d: float | None = None
    avg_rel_volume: float | None = None
    breadth_pct: float | None = None  # share of constituents that are up on the day
    momentum: float | None = None  # average RSI of constituents
    trend: Literal["UP", "DOWN", "SIDEWAYS", "UNKNOWN"] = "UNKNOWN"
    rank: int | None = None


class MarketContext(BaseModel):
    as_of: datetime
    market_state: MarketState
    market_state_note: str
    indices: list[IndexSnapshot]
    india_vix: float | None = None
    india_vix_change_pct: float | None = None
    breadth: Breadth | None = None
    regime: MarketRegime
    sectors: list[SectorSnapshot] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)
    provenance: Provenance


# ---- verification ---------------------------------------------------------------------------------------
class SourceValue(BaseModel):
    source: str
    origin: str
    value: float | str | bool
    data_as_of: datetime | None = None
    reliability: float = Field(ge=0, le=1)


class VerificationClaim(BaseModel):
    key: str
    claim: str
    status: VerificationStatus
    confidence: float = Field(ge=0, le=1)
    sources_checked: int
    independent_origins: int
    values: list[SourceValue]
    tolerance_pct: float | None = None
    detail: str
    resolution: str | None = None  # set only for CONFLICTING claims


class ConfidenceBreakdown(BaseModel):
    source_reliability: float
    freshness: float
    verification: float
    completeness: float
    sample_adequacy: float
    synthetic_cap_applied: bool = False


class VerificationReport(BaseModel):
    claims: list[VerificationClaim]
    conflicts_found: int
    sources_checked: int
    data_confidence: float  # 0..100
    breakdown: ConfidenceBreakdown
    provenance: Provenance


# ---- scoring & the final report ---------------------------------------------------------------------------
class ScoreComponent(BaseModel):
    key: str
    label: str
    points: float
    max_points: float
    available: bool
    rating: Rating
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)


class ScoreResult(BaseModel):
    research_score: float | None  # 0..100, None when nothing could be scored
    raw_score: float | None
    capped: bool = False
    cap_reason: str | None = None
    available_points: float
    total_points: float
    coverage_pct: float
    components: list[ScoreComponent]
    weight_set_id: str | None = None
    weight_set_version: int | None = None
    setup_quality: Literal["STRONG", "MODERATE", "WEAK", "UNKNOWN"] = "UNKNOWN"
    direction: Direction = "NEUTRAL"


class ReportOverview(BaseModel):
    price: float
    change: float | None
    change_pct: float | None
    volume: int
    avg_volume: float | None
    market_cap: float | None = None  # not available without a fundamentals source
    sector: str | None
    industry: str | None = None
    exchange: str = "NSE"


class QualityCheckRead(BaseModel):
    key: str
    status: Literal["PASS", "WARN", "FAIL"]
    message: str
    detail: dict[str, Any] | None = None


class AgentTrace(BaseModel):
    agent: str
    label: str
    status: AgentStatus
    confidence: float | None = None
    timestamp: datetime | None = None
    duration_ms: int | None = None
    summary: str
    findings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    symbol: str
    company: str
    sector: str | None
    run_id: str
    generated_at: datetime
    as_of: datetime
    market_state: MarketState
    data_source: str
    is_synthetic: bool
    research_score: float | None
    data_confidence: float
    risk_score: float | None  # 0 to 100, higher means more risk. Separate from the two numbers above.
    score_coverage_pct: float
    direction: Direction
    setup_quality: Literal["STRONG", "MODERATE", "WEAK", "UNKNOWN"]
    risk_level: RiskLevel
    labels: dict[str, str]
    overview: ReportOverview
    price: PriceBlock
    volatility: VolatilityBlock
    score: ScoreResult
    technical: TechnicalAnalysis
    historical: HistoricalAnalysis | None
    risk: RiskAssessment
    verification: VerificationReport
    market_context: MarketContext
    sector_context: SectorSnapshot | None
    why_listed: list[str]
    risks: list[str]
    invalidation: list[str]
    warnings: list[ResearchWarning]
    sources: list[SourceRef]
    agents: list[AgentTrace]
    not_assessed: list[str]  # what this report could not cover, stated plainly
    quality_status: Literal["PASS", "WARN", "FAIL"] = "PASS"
    quality_checks: list[QualityCheckRead] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
