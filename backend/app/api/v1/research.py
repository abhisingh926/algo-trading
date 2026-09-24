from typing import Literal

from fastapi import APIRouter, Query, Response

from app.core.dependencies import CurrentUser, ServicesDep
from app.core.exceptions import NotAvailableYetError
from app.research.contracts import ResearchReport
from app.schemas.common import ApiResponse, ok
from app.schemas.research import (
    CandidateList,
    CandidateRead,
    MarketOverview,
    ReportSummary,
    ResearchRunRead,
    ResearchSummaryRead,
    RiskView,
    RunRequest,
    ScoreHistory,
    SectorOverview,
    SourceRegistryRead,
    SourceRegistryUpdate,
    SourcesView,
    TechnicalView,
    UniverseRead,
    UniverseWrite,
    WeightSetCreate,
    WeightSetRead,
)

router = APIRouter(prefix="/research", tags=["Research"])
_RESEARCH_NOTE = "Research and decision support only. Not investment advice."


# ---- runs -------------------------------------------------------------------------------------------------
@router.post("/run", response_model=ApiResponse[ResearchRunRead], status_code=201)
async def start_run(body: RunRequest, services: ServicesDep, user: CurrentUser):
    """Start a research scan in the background. Poll GET /research/runs/{id} for progress."""
    run = await services.research.create_run(body, user)
    return ok(run, "Research run started", 201, f"Run #{run.run_number} is {run.status.lower()}")


@router.get("/summary", response_model=ApiResponse[ResearchSummaryRead])
async def summary(services: ServicesDep):
    return ok(await services.research.summary(), "Research summary")


@router.get("/runs", response_model=ApiResponse[list[ResearchRunRead]])
async def list_runs(
    services: ServicesDep, limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)
):
    return ok(await services.research.list_runs(limit, offset), "Research runs")


@router.get("/runs/{run_id}", response_model=ApiResponse[ResearchRunRead])
async def get_run(run_id: str, services: ServicesDep):
    return ok(await services.research.get_run(run_id), "Research run")


# ---- candidates ---------------------------------------------------------------------------------------------
@router.get("/candidates", response_model=ApiResponse[CandidateList])
async def candidates(
    services: ServicesDep,
    run_id: str | None = None,
    min_score: float | None = Query(None, ge=0, le=100),
    min_confidence: float | None = Query(None, ge=0, le=100),
    min_rel_volume: float | None = Query(None, ge=0),
    sector: str | None = None,
    risk: Literal["LOW", "MEDIUM", "HIGH"] | None = None,
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: Literal[
        "score", "confidence", "rel_volume", "change", "atr", "price", "symbol", "initial"
    ] = "score",
    order: Literal["desc", "asc"] = "desc",
    include_unanalyzed: bool = False,
    limit: int = Query(200, ge=1, le=500),
):
    """Top Research Candidates from the latest completed run (or `run_id`)."""
    result = await services.research.candidates(
        run_id,
        include_unanalyzed,
        min_score=min_score,
        min_confidence=min_confidence,
        min_rel_volume=min_rel_volume,
        sector=sector or None,
        risk_level=risk,
        direction=direction,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        descending=order == "desc",
        limit=limit,
    )
    return ok(result, "Top research candidates", description=_RESEARCH_NOTE)


@router.get("/candidates/{symbol}", response_model=ApiResponse[CandidateRead])
async def candidate(symbol: str, services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.candidate(symbol, run_id), f"Research candidate {symbol.upper()}")


# ---- market, sectors ----------------------------------------------------------------------------------------
@router.get("/market", response_model=ApiResponse[MarketOverview])
async def market(services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.market(run_id), "Market overview")


@router.get("/sectors", response_model=ApiResponse[SectorOverview])
async def sectors(services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.sectors(run_id), "Sector rotation")


# ---- scoring weights (changes need explicit approval) ------------------------------------------------------------
@router.get("/weights", response_model=ApiResponse[list[WeightSetRead]])
async def list_weights(services: ServicesDep):
    return ok(
        [WeightSetRead.model_validate(w) for w in await services.research.list_weights()],
        "Scoring weight sets",
    )


@router.post("/weights", response_model=ApiResponse[WeightSetRead], status_code=201)
async def propose_weights(body: WeightSetCreate, services: ServicesDep, user: CurrentUser):
    """Propose a new weight set. It changes nothing until an administrator approves it."""
    weight_set = await services.research.propose_weights(body, user)
    return ok(
        WeightSetRead.model_validate(weight_set),
        "Weight set proposed",
        201,
        "Proposed. Scoring is unchanged until it is approved.",
    )


@router.post("/weights/{weight_id}/approve", response_model=ApiResponse[WeightSetRead])
async def approve_weights(weight_id: str, services: ServicesDep, user: CurrentUser):
    return ok(
        WeightSetRead.model_validate(await services.research.approve_weights(weight_id, user)),
        "Weight set approved and activated",
    )


# ---- source registry and universes ------------------------------------------------------------------------------
@router.get("/source-registry", response_model=ApiResponse[list[SourceRegistryRead]])
async def source_registry(services: ServicesDep):
    return ok(
        [SourceRegistryRead.model_validate(s) for s in await services.research.list_sources()],
        "Source registry",
    )


@router.put("/source-registry/{source_id}", response_model=ApiResponse[SourceRegistryRead])
async def update_source(source_id: str, body: SourceRegistryUpdate, services: ServicesDep):
    updated = await services.research.update_source(source_id, body.model_dump(exclude_unset=True))
    return ok(SourceRegistryRead.model_validate(updated), "Source updated")


@router.get("/universes", response_model=ApiResponse[list[UniverseRead]])
async def universes(services: ServicesDep):
    return ok(await services.research.list_universes(), "Research universes")


@router.get("/universes/{name}", response_model=ApiResponse[UniverseRead])
async def universe(name: str, services: ServicesDep):
    return ok(await services.research.universe(name), "Universe")


@router.put("/universes/{name}", response_model=ApiResponse[UniverseRead])
async def replace_universe(name: str, body: UniverseWrite, services: ServicesDep):
    return ok(await services.research.replace_universe(name, body), "Universe updated")


# ---- calibration: did the scores correspond to anything? ----------------------------------------------------------
@router.post("/runs/{run_id}/calibrate", response_model=ApiResponse[dict])
async def calibrate_run(run_id: str, services: ServicesDep, force: bool = False):
    """Measure the market that followed each score in this run. Needs an hour of trading to have passed."""
    result = await services.calibration.calibrate_run(run_id, force=force)
    return ok(result, "Calibration complete", description=result["summary"]["verdict"])


@router.get("/runs/{run_id}/calibration", response_model=ApiResponse[dict])
async def run_calibration(run_id: str, services: ServicesDep):
    return ok(await services.calibration.run_results(run_id), "Run calibration")


@router.get("/calibration", response_model=ApiResponse[dict])
async def calibration(services: ServicesDep):
    """Outcomes by score bucket across every calibrated run. Measured results, not a prediction."""
    result = await services.calibration.overall()
    return ok(result, "Score calibration", description=result["summary"]["verdict"])


@router.get("/calibration/pending", response_model=ApiResponse[list[dict]])
async def calibration_pending(services: ServicesDep):
    return ok(await services.calibration.pending_runs(), "Runs ready to calibrate")


# ---- per stock (declared last so fixed paths above win) -----------------------------------------------------------
@router.get("/{symbol}", response_model=ApiResponse[ResearchReport])
async def report(symbol: str, services: ServicesDep, run_id: str | None = None):
    """The complete research report for one stock."""
    return ok(
        await services.research.report(symbol, run_id),
        f"Research report for {symbol.upper()}",
        description=_RESEARCH_NOTE,
    )


@router.get("/{symbol}/history", response_model=ApiResponse[list[ReportSummary]])
async def history(symbol: str, services: ServicesDep, limit: int = Query(30, ge=1, le=200)):
    return ok(await services.research.history(symbol, limit), "Research history")


@router.get("/{symbol}/score-history", response_model=ApiResponse[ScoreHistory])
async def score_history(symbol: str, services: ServicesDep, limit: int = Query(30, ge=2, le=200)):
    """Score over time, with an explanation of each change."""
    return ok(await services.research.score_history(symbol, limit), "Score history")


@router.get("/{symbol}/technical", response_model=ApiResponse[TechnicalView])
async def technical(symbol: str, services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.technical(symbol, run_id), "Technical analysis")


@router.get("/{symbol}/risk", response_model=ApiResponse[RiskView])
async def risk(symbol: str, services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.risk(symbol, run_id), "Risk assessment")


@router.get("/{symbol}/sources", response_model=ApiResponse[SourcesView])
async def sources(symbol: str, services: ServicesDep, run_id: str | None = None):
    return ok(await services.research.sources(symbol, run_id), "Sources and verification")


@router.get("/{symbol}/verification", response_model=ApiResponse[SourcesView])
async def verification(symbol: str, services: ServicesDep, run_id: str | None = None):
    """Claims, their status and the sources behind them."""
    return ok(await services.research.sources(symbol, run_id), "Data verification")


@router.get("/{symbol}/agent-trace", response_model=ApiResponse[list[dict]])
async def agent_trace(symbol: str, services: ServicesDep, run_id: str | None = None):
    """What each agent did for this report, so the research is auditable."""
    return ok(await services.research.agent_trace(symbol, run_id), "Agent trace")


@router.get("/{symbol}/corporate-events")
async def corporate_events(symbol: str):
    raise NotAvailableYetError(
        "No corporate events source is connected yet. Results, board meetings and corporate actions are planned "
        "for phase 2 and need exchange filings or a data vendor."
    )


@router.get("/{symbol}/derivatives")
async def derivatives(symbol: str):
    raise NotAvailableYetError(
        "No derivatives data source is connected yet. Futures, open interest, options chain, put-call ratio and "
        "implied volatility need an options and futures feed."
    )


@router.get("/{symbol}/news")
async def news(symbol: str):
    raise NotAvailableYetError(
        "No news source is connected yet. News and catalyst analysis is planned for phase 2 and needs a licensed or permitted feed plus an LLM key."
    )


@router.get("/{symbol}/fundamentals")
async def fundamentals(symbol: str):
    raise NotAvailableYetError(
        "No fundamentals data source is connected yet. Fundamental analysis is planned for phase 3 and needs a data vendor subscription."
    )


@router.get("/{symbol}/export")
async def export(
    symbol: str, services: ServicesDep, format: Literal["json", "csv"] = "json", run_id: str | None = None
):
    content, media_type, filename = await services.research.export(symbol, format, run_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
