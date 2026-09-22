"""Research module tables. Searchable facts are normalised columns; flexible agent output lives in JSON columns."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow
from app.models.base import TimestampMixin, UUIDMixin


class ResearchWeightSet(UUIDMixin, TimestampMixin, Base):
    """Scoring weights and thresholds. Only an explicit approval makes a set ACTIVE; nothing changes them automatically."""

    __tablename__ = "research_weight_sets"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(12), default="PROPOSED", index=True
    )  # ACTIVE | PROPOSED | ARCHIVED
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ResearchSource(UUIDMixin, TimestampMixin, Base):
    """Source registry. `connected` says whether an adapter exists; nothing is scraped from a source marked False."""

    __tablename__ = "research_sources"

    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )  # 1 = official, 2 = reliable, 3 = other
    base_url: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ResearchUniverseMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_universe_members"
    __table_args__ = (UniqueConstraint("universe", "symbol", "exchange"),)

    universe: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    sector: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(80))
    added_on: Mapped[date | None] = mapped_column(
        Date
    )  # None = unknown; membership history is not reconstructed
    removed_on: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)


class ResearchRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_runs"
    __table_args__ = (Index("ix_research_runs_status_created", "status", "created_at"),)

    run_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), default="PENDING", nullable=False
    )  # PENDING RUNNING COMPLETED FAILED
    market: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    universe: Mapped[str] = mapped_column(String(30), nullable=False)
    research_type: Mapped[str] = mapped_column(String(20), default="INTRADAY", nullable=False)
    depth: Mapped[str] = mapped_column(String(10), nullable=False)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    market_state: Mapped[str | None] = mapped_column(String(15))
    data_source: Mapped[str | None] = mapped_column(String(30))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_weight_sets.id", ondelete="SET NULL")
    )
    requested_symbols: Mapped[list[str] | None] = mapped_column(JSON)
    candidates_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conflicts_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    agent_runs: Mapped[list[ResearchAgentRun]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="noload"
    )


class ResearchAgentRun(UUIDMixin, Base):
    __tablename__ = "research_agent_runs"
    __table_args__ = (UniqueConstraint("run_id", "agent"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings: Mapped[list[str] | None] = mapped_column(JSON)
    message: Mapped[str | None] = mapped_column(Text)

    run: Mapped[ResearchRun] = relationship(back_populates="agent_runs")


class ResearchAgentOutput(UUIDMixin, Base):
    __tablename__ = "research_agent_outputs"
    __table_args__ = (Index("ix_research_agent_outputs_run_symbol", "run_id", "symbol"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50))
    agent: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    data_as_of: Mapped[datetime | None] = mapped_column(UTCDateTime)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ResearchCandidate(UUIDMixin, Base):
    __tablename__ = "research_candidates"
    __table_args__ = (UniqueConstraint("run_id", "symbol"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sector: Mapped[str | None] = mapped_column(String(50))
    stage: Mapped[str] = mapped_column(String(10), nullable=False)  # SCANNED SELECTED ANALYZED EXCLUDED
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    initial_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ResearchScore(UUIDMixin, Base):
    __tablename__ = "research_scores"
    __table_args__ = (
        UniqueConstraint("run_id", "symbol"),
        Index("ix_research_scores_run_score", "run_id", "research_score"),
        Index("ix_research_scores_symbol_asof", "symbol", "as_of"),
    )

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    company: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sector: Mapped[str | None] = mapped_column(String(50))
    as_of: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    research_score: Mapped[float | None] = mapped_column(Float)
    data_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    setup_quality: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(8), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    capped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_weight_sets.id", ondelete="SET NULL")
    )
    price: Mapped[float | None] = mapped_column(Float)
    change_pct: Mapped[float | None] = mapped_column(Float)
    rel_volume: Mapped[float | None] = mapped_column(Float)
    atr_pct: Mapped[float | None] = mapped_column(Float)
    vwap: Mapped[float | None] = mapped_column(Float)
    vwap_position: Mapped[str | None] = mapped_column(String(6))
    initial_score: Mapped[float | None] = mapped_column(Float)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    components: Mapped[list[ResearchScoreComponent]] = relationship(
        back_populates="score", cascade="all, delete-orphan", lazy="noload"
    )


class ResearchScoreComponent(UUIDMixin, Base):
    __tablename__ = "research_score_components"

    score_id: Mapped[str] = mapped_column(ForeignKey("research_scores.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(24), nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    max_points: Mapped[float] = mapped_column(Float, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rating: Mapped[str] = mapped_column(String(12), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    score: Mapped[ResearchScore] = relationship(back_populates="components")


class ResearchClaim(UUIDMixin, Base):
    __tablename__ = "research_claims"
    __table_args__ = (Index("ix_research_claims_run_symbol", "run_id", "symbol"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    claim_key: Mapped[str] = mapped_column(String(40), nullable=False)
    claim_text: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    verification: Mapped[ResearchVerification | None] = relationship(
        back_populates="claim", cascade="all, delete-orphan", uselist=False, lazy="noload"
    )


class ResearchVerification(UUIDMixin, Base):
    __tablename__ = "research_verifications"

    claim_id: Mapped[str] = mapped_column(ForeignKey("research_claims.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sources_checked: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_origins: Mapped[int] = mapped_column(Integer, nullable=False)
    tolerance_pct: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str | None] = mapped_column(Text)
    source_values: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    claim: Mapped[ResearchClaim] = relationship(back_populates="verification")


class ResearchMarketSnapshot(UUIDMixin, Base):
    __tablename__ = "research_market_snapshots"

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), unique=True)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    market_state: Mapped[str] = mapped_column(String(15), nullable=False)
    regime: Mapped[str] = mapped_column(String(16), nullable=False)
    regime_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    nifty_price: Mapped[float | None] = mapped_column(Float)
    nifty_change_pct: Mapped[float | None] = mapped_column(Float)
    banknifty_price: Mapped[float | None] = mapped_column(Float)
    banknifty_change_pct: Mapped[float | None] = mapped_column(Float)
    india_vix: Mapped[float | None] = mapped_column(Float)
    advances: Mapped[int | None] = mapped_column(Integer)
    declines: Mapped[int | None] = mapped_column(Integer)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ResearchSectorSnapshot(UUIDMixin, Base):
    __tablename__ = "research_sector_snapshots"

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), index=True)
    sector: Mapped[str] = mapped_column(String(50), nullable=False)
    constituents: Mapped[int] = mapped_column(Integer, nullable=False)
    ret_1d_pct: Mapped[float | None] = mapped_column(Float)
    ret_5d_pct: Mapped[float | None] = mapped_column(Float)
    rel_strength_1d: Mapped[float | None] = mapped_column(Float)
    rel_strength_5d: Mapped[float | None] = mapped_column(Float)
    avg_rel_volume: Mapped[float | None] = mapped_column(Float)
    breadth_pct: Mapped[float | None] = mapped_column(Float)
    momentum: Mapped[float | None] = mapped_column(Float)
    trend: Mapped[str] = mapped_column(String(10), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)


class ResearchHistoricalPattern(UUIDMixin, Base):
    __tablename__ = "research_historical_patterns"
    __table_args__ = (Index("ix_research_patterns_run_symbol", "run_id", "symbol"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    horizon: Mapped[str] = mapped_column(String(16), nullable=False)
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False)
    successful: Mapped[int | None] = mapped_column(Integer)
    success_rate: Mapped[float | None] = mapped_column(Float)
    avg_return_pct: Mapped[float | None] = mapped_column(Float)
    median_return_pct: Mapped[float | None] = mapped_column(Float)
    avg_return_net_pct: Mapped[float | None] = mapped_column(Float)
    mfe_pct: Mapped[float | None] = mapped_column(Float)
    mae_pct: Mapped[float | None] = mapped_column(Float)
    sample_adequate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    min_sample: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[str | None] = mapped_column(String(10))
    period_end: Mapped[str | None] = mapped_column(String(10))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ResearchRiskEvent(UUIDMixin, Base):
    __tablename__ = "research_risk_events"
    __table_args__ = (Index("ix_research_risk_events_run_symbol", "run_id", "symbol"),)

    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(String(40))
    value: Mapped[float | None] = mapped_column(Float)
