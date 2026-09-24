from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.research.contracts import (
    IntradayLevels,
    MarketContext,
    PriceBlock,
    Provenance,
    ResearchWarning,
    RiskAssessment,
    SectorSnapshot,
    SourceRef,
    TechnicalAnalysis,
    VerificationClaim,
    VolatilityBlock,
)
from app.research.explain import ScoreChange
from app.schemas.common import ORMModel


class RunRequest(BaseModel):
    market: Literal["NSE"] = "NSE"
    universe: str = Field(default="NIFTY50", min_length=1, max_length=30)
    symbols: list[str] | None = Field(default=None, description="Required when universe is CUSTOM")
    research_type: Literal["INTRADAY"] = "INTRADAY"
    depth: Literal["QUICK", "STANDARD", "DEEP"] = "STANDARD"
    as_of: datetime | None = Field(
        default=None, description="Analyse the market as it was at this time. Defaults to now."
    )

    @field_validator("universe")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("symbols")
    @classmethod
    def _symbols(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = list(dict.fromkeys(s.strip().upper() for s in value if s.strip()))
        if len(cleaned) > 100:
            raise ValueError("At most 100 symbols per run")
        return cleaned


class AgentRunRead(ORMModel):
    agent: str
    label: str = ""
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    records: int
    warnings: list[str] | None
    message: str | None


class ResearchRunRead(ORMModel):
    id: str
    run_number: int
    status: str
    market: str
    universe: str
    research_type: str
    depth: str
    as_of: datetime
    is_live: bool
    market_state: str | None
    data_source: str | None
    is_synthetic: bool
    weight_set_id: str | None
    requested_symbols: list[str] | None
    candidates_scanned: int
    candidates_analyzed: int
    sources_checked: int
    conflicts_found: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    created_at: datetime
    agents: list[AgentRunRead] = Field(default_factory=list)


class CandidateRead(BaseModel):
    rank: int | None
    symbol: str
    company: str
    sector: str | None
    stage: str
    exclusion_reason: str | None = None
    price: float | None
    change_pct: float | None
    rel_volume: float | None
    atr_pct: float | None
    vwap: float | None
    vwap_position: str | None
    research_score: float | None
    data_confidence: float | None
    risk_score: float | None = None
    coverage_pct: float | None
    risk_level: str | None
    direction: str | None
    setup_quality: str | None
    catalyst: str = "Not assessed"
    initial_score: float | None
    warning_count: int = 0
    reasons: list[str] = Field(default_factory=list)
    as_of: datetime | None
    run_id: str


class CandidateList(BaseModel):
    run: ResearchRunRead | None
    items: list[CandidateRead]
    sectors: list[str]
    total: int


class TechnicalView(BaseModel):
    symbol: str
    run_id: str
    as_of: datetime
    price: PriceBlock
    volatility: VolatilityBlock
    technical: TechnicalAnalysis
    levels: IntradayLevels


class RiskView(BaseModel):
    symbol: str
    run_id: str
    as_of: datetime
    risk: RiskAssessment
    warnings: list[ResearchWarning]


class SourcesView(BaseModel):
    symbol: str
    run_id: str
    sources: list[SourceRef]
    claims: list[VerificationClaim]
    data_confidence: float
    provenance: list[Provenance]


class ReportSummary(BaseModel):
    run_id: str
    run_number: int | None
    as_of: datetime
    research_score: float | None
    data_confidence: float
    risk_score: float | None = None
    direction: str
    setup_quality: str
    risk_level: str
    rank: int | None
    is_synthetic: bool


class ScorePoint(BaseModel):
    run_id: str
    as_of: datetime
    research_score: float | None
    data_confidence: float
    risk_score: float | None = None
    direction: str
    risk_level: str


class ScoreHistory(BaseModel):
    symbol: str
    points: list[ScorePoint]
    changes: list[ScoreChange]


class WeightSetRead(ORMModel):
    id: str
    name: str
    version: int
    status: str
    weights: dict[str, Any]
    thresholds: dict[str, Any]
    notes: str | None
    created_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class WeightSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    weights: dict[str, float]
    thresholds: dict[str, float] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=1000)


class SourceRegistryRead(ORMModel):
    id: str
    key: str
    name: str
    source_type: str
    priority: int
    base_url: str | None
    enabled: bool
    connected: bool
    rate_limit_per_minute: int | None
    reliability_score: float
    supports_market_data: bool = False
    supports_news: bool = False
    supports_filings: bool = False
    supports_fundamentals: bool = False
    supports_derivatives: bool = False
    notes: str | None


class SourceRegistryUpdate(BaseModel):
    enabled: bool | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=1)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    base_url: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class UniverseMemberRead(BaseModel):
    symbol: str
    sector: str | None
    company: str | None = None


class UniverseRead(BaseModel):
    name: str
    count: int
    members: list[UniverseMemberRead] = Field(default_factory=list)
    note: str | None = None


class UniverseMemberWrite(BaseModel):
    symbol: str
    sector: str | None = None

    @field_validator("symbol")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class UniverseWrite(BaseModel):
    members: list[UniverseMemberWrite] = Field(min_length=1, max_length=600)


class MarketOverview(BaseModel):
    run_id: str
    run_number: int
    generated_at: datetime
    is_synthetic: bool
    data_source: str | None
    context: MarketContext


class SectorOverview(BaseModel):
    run_id: str
    run_number: int
    as_of: datetime
    is_synthetic: bool
    sectors: list[SectorSnapshot]


class ResearchSummaryRead(BaseModel):
    """Small payload for the dashboard: is research available and what was the latest run."""

    latest_run: ResearchRunRead | None
    active_run: ResearchRunRead | None
