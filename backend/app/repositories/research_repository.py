"""Persistence for the research module. Services never touch SQLAlchemy directly."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select, update

from app.models.research import (
    ResearchAgentOutput,
    ResearchAgentRun,
    ResearchCalibrationResult,
    ResearchCandidate,
    ResearchClaim,
    ResearchDataQualityEvent,
    ResearchHistoricalPattern,
    ResearchMarketSnapshot,
    ResearchRiskEvent,
    ResearchRun,
    ResearchScore,
    ResearchScoreComponent,
    ResearchSectorSnapshot,
    ResearchSource,
    ResearchUniverseMember,
    ResearchVerification,
    ResearchWeightSet,
)
from app.repositories.base import BaseRepository
from app.utils.time import utcnow

_SORTABLE = {
    "score": ResearchScore.research_score,
    "confidence": ResearchScore.data_confidence,
    "rel_volume": ResearchScore.rel_volume,
    "change": ResearchScore.change_pct,
    "atr": ResearchScore.atr_pct,
    "price": ResearchScore.price,
    "symbol": ResearchScore.symbol,
    "initial": ResearchScore.initial_score,
}


class ResearchRunRepository(BaseRepository[ResearchRun]):
    model = ResearchRun

    async def next_run_number(self) -> int:
        return int(
            await self.session.scalar(select(func.coalesce(func.max(ResearchRun.run_number), 999) + 1))
            or 1000
        )

    async def list_recent(self, limit: int = 50, offset: int = 0) -> Sequence[ResearchRun]:
        stmt = select(ResearchRun).order_by(ResearchRun.run_number.desc()).limit(limit).offset(offset)
        return (await self.session.scalars(stmt)).all()

    async def latest_completed(self, universe: str | None = None) -> ResearchRun | None:
        stmt = select(ResearchRun).where(ResearchRun.status == "COMPLETED")
        if universe:
            stmt = stmt.where(ResearchRun.universe == universe)
        return await self.session.scalar(stmt.order_by(ResearchRun.run_number.desc()).limit(1))

    async def active_run(self) -> ResearchRun | None:
        stmt = select(ResearchRun).where(ResearchRun.status.in_(["PENDING", "RUNNING"])).limit(1)
        return await self.session.scalar(stmt)

    async def fail_orphans(self, message: str) -> int:
        result = await self.session.execute(
            update(ResearchRun)
            .where(ResearchRun.status.in_(["PENDING", "RUNNING"]))
            .values(status="FAILED", error_message=message, completed_at=utcnow())
        )
        return int(result.rowcount or 0)


class ResearchAgentRunRepository(BaseRepository[ResearchAgentRun]):
    model = ResearchAgentRun

    async def for_run(self, run_id: str) -> Sequence[ResearchAgentRun]:
        stmt = select(ResearchAgentRun).where(ResearchAgentRun.run_id == run_id)
        return (await self.session.scalars(stmt)).all()

    async def get(self, run_id: str, agent: str) -> ResearchAgentRun | None:
        stmt = select(ResearchAgentRun).where(
            ResearchAgentRun.run_id == run_id, ResearchAgentRun.agent == agent
        )
        return await self.session.scalar(stmt)


class ResearchScoreRepository(BaseRepository[ResearchScore]):
    model = ResearchScore

    async def list_for_run(
        self,
        run_id: str,
        *,
        min_score: float | None = None,
        min_confidence: float | None = None,
        min_rel_volume: float | None = None,
        sector: str | None = None,
        risk_level: str | None = None,
        direction: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "score",
        descending: bool = True,
        limit: int = 200,
    ) -> Sequence[ResearchScore]:
        stmt = select(ResearchScore).where(ResearchScore.run_id == run_id)
        if min_score is not None:
            stmt = stmt.where(ResearchScore.research_score >= min_score)
        if min_confidence is not None:
            stmt = stmt.where(ResearchScore.data_confidence >= min_confidence)
        if min_rel_volume is not None:
            stmt = stmt.where(ResearchScore.rel_volume >= min_rel_volume)
        if sector:
            stmt = stmt.where(ResearchScore.sector == sector)
        if risk_level:
            stmt = stmt.where(ResearchScore.risk_level == risk_level)
        if direction:
            stmt = stmt.where(ResearchScore.direction == direction)
        if min_price is not None:
            stmt = stmt.where(ResearchScore.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(ResearchScore.price <= max_price)
        column = _SORTABLE.get(sort, ResearchScore.research_score)
        stmt = stmt.order_by(column.desc() if descending else column.asc(), ResearchScore.symbol.asc()).limit(
            limit
        )
        return (await self.session.scalars(stmt)).all()

    async def get_for_run(self, run_id: str, symbol: str) -> ResearchScore | None:
        stmt = select(ResearchScore).where(
            ResearchScore.run_id == run_id, ResearchScore.symbol == symbol.upper()
        )
        return await self.session.scalar(stmt)

    async def latest_for_symbol(self, symbol: str) -> ResearchScore | None:
        stmt = (
            select(ResearchScore)
            .where(ResearchScore.symbol == symbol.upper())
            .order_by(ResearchScore.as_of.desc(), ResearchScore.rank.asc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def history(self, symbol: str, limit: int = 60) -> Sequence[ResearchScore]:
        stmt = (
            select(ResearchScore)
            .where(ResearchScore.symbol == symbol.upper())
            .order_by(ResearchScore.as_of.desc())
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def components(self, score_id: str) -> Sequence[ResearchScoreComponent]:
        stmt = select(ResearchScoreComponent).where(ResearchScoreComponent.score_id == score_id)
        return (await self.session.scalars(stmt)).all()

    async def components_for(self, score_ids: Sequence[str]) -> dict[str, list[ResearchScoreComponent]]:
        if not score_ids:
            return {}
        stmt = select(ResearchScoreComponent).where(ResearchScoreComponent.score_id.in_(list(score_ids)))
        out: dict[str, list[ResearchScoreComponent]] = {}
        for component in (await self.session.scalars(stmt)).all():
            out.setdefault(component.score_id, []).append(component)
        return out

    async def sectors(self, run_id: str) -> list[str]:
        stmt = (
            select(ResearchScore.sector)
            .where(ResearchScore.run_id == run_id, ResearchScore.sector.is_not(None))
            .distinct()
        )
        return sorted(s for (s,) in (await self.session.execute(stmt)).all())

    async def add_with_components(
        self, score: ResearchScore, components: list[ResearchScoreComponent]
    ) -> None:
        self.session.add(score)
        await self.session.flush()
        for component in components:
            component.score_id = score.id
        self.session.add_all(components)


class ResearchCandidateRepository(BaseRepository[ResearchCandidate]):
    model = ResearchCandidate

    async def list_for_run(self, run_id: str, stage: str | None = None) -> Sequence[ResearchCandidate]:
        stmt = select(ResearchCandidate).where(ResearchCandidate.run_id == run_id)
        if stage:
            stmt = stmt.where(ResearchCandidate.stage == stage)
        return (await self.session.scalars(stmt.order_by(ResearchCandidate.initial_score.desc()))).all()

    async def get_for_run(self, run_id: str, symbol: str) -> ResearchCandidate | None:
        stmt = select(ResearchCandidate).where(
            ResearchCandidate.run_id == run_id, ResearchCandidate.symbol == symbol.upper()
        )
        return await self.session.scalar(stmt)

    async def add_many(self, rows: list[ResearchCandidate]) -> None:
        self.session.add_all(rows)
        await self.session.flush()


class ResearchOutputRepository(BaseRepository[ResearchAgentOutput]):
    model = ResearchAgentOutput

    async def for_symbol(self, run_id: str, symbol: str) -> Sequence[ResearchAgentOutput]:
        stmt = select(ResearchAgentOutput).where(
            ResearchAgentOutput.run_id == run_id, ResearchAgentOutput.symbol == symbol.upper()
        )
        return (await self.session.scalars(stmt)).all()

    async def add_many(self, rows: list[ResearchAgentOutput]) -> None:
        self.session.add_all(rows)


class ResearchClaimRepository(BaseRepository[ResearchClaim]):
    model = ResearchClaim

    async def add_with_verification(self, claim: ResearchClaim, verification: ResearchVerification) -> None:
        self.session.add(claim)
        await self.session.flush()
        verification.claim_id = claim.id
        self.session.add(verification)

    async def for_symbol(self, run_id: str, symbol: str) -> list[tuple[ResearchClaim, ResearchVerification]]:
        stmt = (
            select(ResearchClaim, ResearchVerification)
            .join(ResearchVerification, ResearchVerification.claim_id == ResearchClaim.id)
            .where(ResearchClaim.run_id == run_id, ResearchClaim.symbol == symbol.upper())
        )
        return [(c, v) for c, v in (await self.session.execute(stmt)).all()]


class ResearchSnapshotRepository(BaseRepository[ResearchMarketSnapshot]):
    model = ResearchMarketSnapshot

    async def market_for_run(self, run_id: str) -> ResearchMarketSnapshot | None:
        return await self.session.scalar(
            select(ResearchMarketSnapshot).where(ResearchMarketSnapshot.run_id == run_id)
        )

    async def sectors_for_run(self, run_id: str) -> Sequence[ResearchSectorSnapshot]:
        stmt = (
            select(ResearchSectorSnapshot)
            .where(ResearchSectorSnapshot.run_id == run_id)
            .order_by(ResearchSectorSnapshot.rank.asc())
        )
        return (await self.session.scalars(stmt)).all()

    async def add_sectors(self, rows: list[ResearchSectorSnapshot]) -> None:
        self.session.add_all(rows)


class ResearchPatternRepository(BaseRepository[ResearchHistoricalPattern]):
    model = ResearchHistoricalPattern

    async def add_many(self, rows: list[ResearchHistoricalPattern]) -> None:
        self.session.add_all(rows)

    async def for_symbol(self, run_id: str, symbol: str) -> Sequence[ResearchHistoricalPattern]:
        stmt = select(ResearchHistoricalPattern).where(
            ResearchHistoricalPattern.run_id == run_id, ResearchHistoricalPattern.symbol == symbol.upper()
        )
        return (await self.session.scalars(stmt)).all()


class ResearchRiskEventRepository(BaseRepository[ResearchRiskEvent]):
    model = ResearchRiskEvent

    async def add_many(self, rows: list[ResearchRiskEvent]) -> None:
        self.session.add_all(rows)

    async def for_symbol(self, run_id: str, symbol: str) -> Sequence[ResearchRiskEvent]:
        stmt = select(ResearchRiskEvent).where(
            ResearchRiskEvent.run_id == run_id, ResearchRiskEvent.symbol == symbol.upper()
        )
        return (await self.session.scalars(stmt)).all()


class ResearchSourceRepository(BaseRepository[ResearchSource]):
    model = ResearchSource

    async def list_sources(self) -> Sequence[ResearchSource]:
        return (
            await self.session.scalars(
                select(ResearchSource).order_by(ResearchSource.priority, ResearchSource.name)
            )
        ).all()

    async def get_by_key(self, key: str) -> ResearchSource | None:
        return await self.session.scalar(select(ResearchSource).where(ResearchSource.key == key))


class ResearchWeightRepository(BaseRepository[ResearchWeightSet]):
    model = ResearchWeightSet

    async def active(self) -> ResearchWeightSet | None:
        return await self.session.scalar(
            select(ResearchWeightSet)
            .where(ResearchWeightSet.status == "ACTIVE")
            .order_by(ResearchWeightSet.version.desc())
            .limit(1)
        )

    async def list_sets(self) -> Sequence[ResearchWeightSet]:
        return (
            await self.session.scalars(select(ResearchWeightSet).order_by(ResearchWeightSet.version.desc()))
        ).all()

    async def next_version(self) -> int:
        return int(
            await self.session.scalar(select(func.coalesce(func.max(ResearchWeightSet.version), 0) + 1)) or 1
        )

    async def archive_active(self) -> None:
        await self.session.execute(
            update(ResearchWeightSet).where(ResearchWeightSet.status == "ACTIVE").values(status="ARCHIVED")
        )


class ResearchUniverseRepository(BaseRepository[ResearchUniverseMember]):
    model = ResearchUniverseMember

    async def members(self, universe: str) -> Sequence[ResearchUniverseMember]:
        stmt = (
            select(ResearchUniverseMember)
            .where(ResearchUniverseMember.universe == universe, ResearchUniverseMember.removed_on.is_(None))
            .order_by(ResearchUniverseMember.symbol)
        )
        return (await self.session.scalars(stmt)).all()

    async def sector_map(self, symbols: Sequence[str]) -> dict[str, str | None]:
        if not symbols:
            return {}
        stmt = select(ResearchUniverseMember.symbol, ResearchUniverseMember.sector).where(
            ResearchUniverseMember.symbol.in_(list(symbols))
        )
        out: dict[str, str | None] = {}
        for symbol, sector in (await self.session.execute(stmt)).all():
            out.setdefault(symbol, sector)
        return out

    async def universes(self) -> list[tuple[str, int]]:
        stmt = (
            select(ResearchUniverseMember.universe, func.count())
            .where(ResearchUniverseMember.removed_on.is_(None))
            .group_by(ResearchUniverseMember.universe)
        )
        return [(u, int(c)) for u, c in (await self.session.execute(stmt)).all()]

    async def add_many(self, rows: list[ResearchUniverseMember]) -> None:
        self.session.add_all(rows)
        await self.session.flush()  # sessions do not autoflush, and callers read the members back straight away

    async def clear(self, universe: str) -> None:
        await self.session.execute(
            delete(ResearchUniverseMember).where(ResearchUniverseMember.universe == universe)
        )


class ResearchCalibrationRepository(BaseRepository[ResearchCalibrationResult]):
    model = ResearchCalibrationResult

    async def for_run(self, run_id: str) -> Sequence[ResearchCalibrationResult]:
        stmt = (
            select(ResearchCalibrationResult)
            .where(ResearchCalibrationResult.run_id == run_id)
            .order_by(ResearchCalibrationResult.research_score.desc())
        )
        return (await self.session.scalars(stmt)).all()

    async def all_results(self, limit: int = 20000) -> Sequence[ResearchCalibrationResult]:
        stmt = select(ResearchCalibrationResult).order_by(ResearchCalibrationResult.as_of.asc()).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def calibrated_run_ids(self) -> set[str]:
        stmt = select(ResearchCalibrationResult.run_id).distinct()
        return {rid for (rid,) in (await self.session.execute(stmt)).all()}

    async def replace_for_run(self, run_id: str, rows: list[ResearchCalibrationResult]) -> None:
        await self.session.execute(
            delete(ResearchCalibrationResult).where(ResearchCalibrationResult.run_id == run_id)
        )
        self.session.add_all(rows)
        await self.session.flush()


class ResearchQualityRepository(BaseRepository[ResearchDataQualityEvent]):
    model = ResearchDataQualityEvent

    async def for_run(self, run_id: str, symbol: str | None = None) -> Sequence[ResearchDataQualityEvent]:
        stmt = select(ResearchDataQualityEvent).where(ResearchDataQualityEvent.run_id == run_id)
        if symbol:
            stmt = stmt.where(ResearchDataQualityEvent.symbol == symbol.upper())
        return (await self.session.scalars(stmt)).all()

    async def add_many(self, rows: list[ResearchDataQualityEvent]) -> None:
        self.session.add_all(rows)
