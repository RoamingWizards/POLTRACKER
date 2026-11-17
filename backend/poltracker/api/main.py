import json
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import make_session_factory
from ..models import CommitteeIndustryMapping, IngestState, PriceBar, Politician, Security, Trade, TradeContext, TradeContextAnalysis
from ..performance import load_benchmark, load_series, trade_performance
from ..trade_context import NOTICE, SIGNALS, ContextConfig, trade_group_key
from ..trade_context_llm import PROMPT_VERSION
from .ordering import nulls_last, text_order
from .schemas import (
    AiContextOut,
    AiSignalExplanationOut,
    ContextEvidenceOut,
    DailyCount,
    MonthlyCount,
    OverviewOut,
    OverviewTotals,
    StatusOut,
    TopPolitician,
    TopTicker,
    PoliticianDetailOut,
    PoliticianOut,
    PoliticianPageOut,
    PriceSeriesOut,
    SecurityOut,
    SecurityPerformanceOut,
    TradeContextOut,
    TradeOut,
    TradePageOut,
    TradePerformanceOut,
)

router = APIRouter()

_session_factory = None


def get_session() -> Iterator[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory()
    with _session_factory() as session:
        yield session


@router.get("/health")
def health(request: Request) -> dict[str, str | bool]:
    # The public API answers exactly {"status": "ok"}. Only the desktop app adds "desktop": true, so the frontend knows the desktop-only
    # routes (/refresh/status) exist and never has to probe for them and log a 404.
    return {"status": "ok", "desktop": True} if getattr(request.app.state, "desktop", False) else {"status": "ok"}


def _context_key(session: Session) -> tuple[str, str] | None:
    """The current context: the default engine version evaluated against the most recently loaded mapping version."""
    mapping_version = session.scalar(select(CommitteeIndustryMapping.mapping_version).order_by(CommitteeIndustryMapping.id.desc()).limit(1))
    return (ContextConfig().version_label(), mapping_version) if mapping_version else None


def _ai_out(a: TradeContextAnalysis | None) -> AiContextOut | None:
    if a is None:
        return None
    return AiContextOut(headline=a.headline, summary=a.summary, signals=[AiSignalExplanationOut(**s) for s in json.loads(a.signals_json)], limitations=a.limitations,
                        generated_for=a.generated_for, model=a.model, prompt_version=a.prompt_version, generated_at=a.created_at)


def _ai_by_trade(session: Session, by_trade: dict[int, TradeContext], key: tuple[str, str]) -> dict[int, TradeContextAnalysis]:
    """Cached explanations that still match the context as it is now (newest first, so the first per trade wins). Optional: if the table does not exist yet
    (a database not yet migrated to 0015) the trades simply have no explanation."""
    found: dict[int, TradeContextAnalysis] = {}
    try:
        with session.begin_nested():
            rows = session.scalars(
                select(TradeContextAnalysis).where(TradeContextAnalysis.trade_id.in_(list(by_trade)), TradeContextAnalysis.context_version == key[0],
                                                   TradeContextAnalysis.mapping_version == key[1], TradeContextAnalysis.prompt_version == PROMPT_VERSION)
                .order_by(TradeContextAnalysis.created_at.desc(), TradeContextAnalysis.id.desc())
            ).all()
    except (OperationalError, ProgrammingError):
        return found
    for a in rows:
        if a.context_digest == by_trade[a.trade_id].result_digest:
            found.setdefault(a.trade_id, a)
    return found


def _trade_outs(session: Session, trades: list[Trade]) -> list[TradeOut]:
    outs = [TradeOut.model_validate(t) for t in trades]
    if trades:  # how many disclosed rows share each group key (display only; nothing is merged)
        pols, dates = {t.politician_id for t in trades}, {t.transaction_date for t in trades}
        counts = Counter(trade_group_key(p, sid, tk, d, ty) for p, sid, tk, d, ty in session.execute(
            select(Trade.politician_id, Trade.security_id, Trade.ticker, Trade.transaction_date, Trade.transaction_type)
            .where(Trade.politician_id.in_(pols), Trade.transaction_date.in_(dates))))
        for o, t in zip(outs, trades):
            o.group_key = trade_group_key(t.politician_id, t.security_id, t.ticker, t.transaction_date, t.transaction_type)
            o.group_size = counts[o.group_key]
    key = _context_key(session)
    if key is None or not outs:
        return outs
    rows = session.scalars(
        select(TradeContext).options(selectinload(TradeContext.evidence))
        .where(TradeContext.trade_id.in_([o.id for o in outs]), TradeContext.context_version == key[0], TradeContext.mapping_version == key[1])
    ).all()
    by_trade = {c.trade_id: c for c in rows}
    ai_by_trade = _ai_by_trade(session, by_trade, key)
    for o in outs:
        c = by_trade.get(o.id)
        if c is not None:
            o.context = TradeContextOut(
                context_version=c.context_version, mapping_version=c.mapping_version, analyzed_at=c.analyzed_at,
                committee_relevance=c.committee_relevance, committee_relevance_reason=c.committee_relevance_reason,
                trade_size_anomaly=c.trade_size_anomaly, trade_size_value=c.trade_size_value, trade_size_basis=c.trade_size_basis,
                trade_size_percentile=c.trade_size_percentile, trade_size_sample_size=c.trade_size_sample_size,
                disclosure_delay_signal=c.disclosure_delay_signal, disclosure_delay_days=c.disclosure_delay_days,
                excess_return_signal=c.excess_return_signal, security_return=c.security_return, spy_return=c.spy_return,
                excess_return=c.excess_return, excess_return_direction_adjusted=c.excess_return_direction_adjusted,
                excess_horizon_days=c.performance_horizon_days,
                signals={name: getattr(c, name) for name in SIGNALS}, signal_count=c.signal_count,
                secondary_signal_count=c.secondary_signal_count, committee_temporal_status=c.committee_temporal_status, meets_flag_rule=c.meets_flag_rule,
                flag_pending_temporal_verification=bool(c.meets_flag_rule and not c.flagged_for_contextual_review),
                flagged_for_contextual_review=c.flagged_for_contextual_review,
                evidence=[ContextEvidenceOut(signal_type=e.signal_type, evidence_type=e.evidence_type, committee_code=e.committee_code,
                                             subcommittee_code=e.subcommittee_code, source_url=e.source_url, description=e.description,
                                             metadata=json.loads(e.metadata_json) if e.metadata_json else None) for e in c.evidence],
                notice=NOTICE,
                ai_context=_ai_out(ai_by_trade.get(o.id)),
            )
    return outs


@router.get("/trades", response_model=TradePageOut)
def list_trades(
    ticker: str | None = None,
    politician_id: int | None = None,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    transaction_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    flagged: bool = Query(False, description="only trades flagged for contextual review (a review aid, not a finding)"),
    sort_by: Literal["transaction_date", "disclosure_date", "amount_min", "ticker", "politician_name"] = "disclosure_date",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> TradePageOut:
    stmt = select(Trade)
    if ticker:
        stmt = stmt.where(Trade.ticker == ticker.upper())
    if politician_id:
        stmt = stmt.where(Trade.politician_id == politician_id)
    if chamber:
        stmt = stmt.where(Trade.chamber == chamber)
    if transaction_type:
        stmt = stmt.where(Trade.transaction_type == transaction_type)
    if date_from:
        stmt = stmt.where(Trade.transaction_date >= date_from)
    if date_to:
        stmt = stmt.where(Trade.transaction_date <= date_to)
    if flagged:
        key = _context_key(session)
        stmt = stmt.where(Trade.id.in_(
            select(TradeContext.trade_id).where(TradeContext.context_version == (key[0] if key else None),
                                                TradeContext.mapping_version == (key[1] if key else None),
                                                TradeContext.flagged_for_contextual_review.is_(True))
        ))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = getattr(Trade, sort_by)
    if sort_by in ("ticker", "politician_name"):
        column = text_order(session, column)
    direction = nulls_last(column.asc() if order == "asc" else column.desc())
    rows = session.scalars(stmt.order_by(direction, Trade.id.desc()).limit(limit).offset(offset)).all()
    return TradePageOut(items=_trade_outs(session, list(rows)), total=total, limit=limit, offset=offset)


@router.get("/trades/{trade_id}", response_model=TradeOut)
def get_trade(trade_id: int, session: Session = Depends(get_session)) -> TradeOut:
    trade = session.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(404, "Trade not found")
    return _trade_outs(session, [trade])[0]


def _politician_out(session: Session, pol: Politician) -> PoliticianOut:
    count, latest = session.execute(
        select(func.count(Trade.id), func.max(Trade.transaction_date)).where(Trade.politician_id == pol.id)
    ).one()
    return PoliticianOut(
        id=pol.id, name=pol.name, chamber=pol.chamber, party=pol.party, state=pol.state,
        trade_count=count, latest_trade_date=latest,
        bioguide_id=pol.bioguide_id, district=pol.district, official_url=pol.official_url, active=pol.active,
        term_start_year=pol.term_start_year, term_end_year=pol.term_end_year, enriched_at=pol.enriched_at,
        enrichment_source=pol.enrichment_source, enrichment_status=pol.enrichment_status, enrichment_method=pol.enrichment_method,
    )


@router.get("/politicians", response_model=PoliticianPageOut)
def list_politicians(
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    q: str | None = Query(None, description="name contains"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> PoliticianPageOut:
    stmt = select(Politician)
    if chamber:
        stmt = stmt.where(Politician.chamber == chamber)
    if q:
        stmt = stmt.where(Politician.name.ilike(f"%{q}%"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pols = session.scalars(stmt.order_by(text_order(session, Politician.name), Politician.id).limit(limit).offset(offset)).all()
    return PoliticianPageOut(items=[_politician_out(session, p) for p in pols], total=total, limit=limit, offset=offset)


@router.get("/politicians/{politician_id}", response_model=PoliticianDetailOut)
def get_politician(politician_id: int, session: Session = Depends(get_session)) -> PoliticianDetailOut:
    pol = session.get(Politician, politician_id)
    if pol is None:
        raise HTTPException(404, "Politician not found")
    seats = sorted(pol.committees, key=lambda c: (c.committee_name, c.subcommittee_name is not None, c.subcommittee_name or ""))
    return PoliticianDetailOut(**_politician_out(session, pol).model_dump(), committees=seats)


@router.get("/securities/{ticker}", response_model=SecurityOut)
def get_security(ticker: str, session: Session = Depends(get_session)) -> SecurityOut:
    sec = session.scalar(select(Security).where(Security.ticker == ticker.upper()))
    if sec is None:
        raise HTTPException(404, "Security not found")
    count, latest = session.execute(
        select(func.count(Trade.id), func.max(Trade.transaction_date)).where(Trade.security_id == sec.id)
    ).one()
    recent = session.scalars(
        select(Trade).where(Trade.security_id == sec.id).order_by(nulls_last(Trade.disclosure_date.desc()), Trade.id.desc()).limit(10)
    ).all()
    return SecurityOut(
        id=sec.id, ticker=sec.ticker, name=sec.name, price_status=sec.price_status,
        price_from=sec.price_from, price_to=sec.price_to,
        trade_count=count, latest_trade_date=latest, recent_trades=recent,
        company_name=sec.company_name, cik=sec.cik, sic_code=sec.sic_code, industry=sec.industry, sector=sec.sector,
        exchange=sec.exchange, profile_status=sec.profile_status, profile_source_url=sec.profile_source_url,
    )


def _security_or_404(session: Session, ticker: str) -> Security:
    sec = session.scalar(select(Security).where(Security.ticker == ticker.upper()))
    if sec is None:
        raise HTTPException(404, "Security not found")
    return sec


@router.get("/securities/{ticker}/prices", response_model=PriceSeriesOut)
def get_prices(
    ticker: str,
    start: date | None = None,
    end: date | None = None,
    session: Session = Depends(get_session),
) -> PriceSeriesOut:
    sec = _security_or_404(session, ticker)
    stmt = select(PriceBar).where(PriceBar.security_id == sec.id)
    if start:
        stmt = stmt.where(PriceBar.date >= start)
    if end:
        stmt = stmt.where(PriceBar.date <= end)
    bars = session.scalars(stmt.order_by(PriceBar.date)).all()
    return PriceSeriesOut(
        ticker=sec.ticker, price_status=sec.price_status, price_from=sec.price_from, price_to=sec.price_to, bars=bars
    )


@router.get("/securities/{ticker}/performance", response_model=SecurityPerformanceOut)
def get_performance(
    ticker: str,
    limit: int = Query(200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> SecurityPerformanceOut:
    sec = _security_or_404(session, ticker)
    bench_ticker = get_settings().benchmark_ticker
    series, bench = load_series(session, sec.id), load_benchmark(session, bench_ticker)
    trades = session.scalars(
        select(Trade).where(Trade.security_id == sec.id).order_by(Trade.transaction_date.desc(), Trade.id.desc()).limit(limit)
    ).all()
    today = date.today()
    items = [
        TradePerformanceOut(trade=t, performance=trade_performance(t, series, bench, bench_ticker, today))
        for t in trades
    ]
    counts = Counter(i.performance.status for i in items)
    return SecurityPerformanceOut(ticker=sec.ticker, benchmark=bench_ticker, status_counts=dict(counts), total=len(items), items=items)



@router.get("/stats/overview", response_model=OverviewOut)
def overview(days: int = Query(30, ge=1, le=365), session: Session = Depends(get_session)) -> OverviewOut:
    today = date.today()
    cutoff = today - timedelta(days=days)
    in_window = Trade.disclosure_date >= cutoff

    buys = func.sum(case((Trade.transaction_type == "buy", 1), else_=0))
    sells = func.sum(case((Trade.transaction_type.in_(("sell", "sell_partial")), 1), else_=0))

    total_trades = session.scalar(select(func.count(Trade.id))) or 0
    win_total, win_buys, win_sells = session.execute(
        select(func.count(Trade.id), buys, sells).where(in_window)
    ).one()

    counts = dict(
        session.execute(
            select(Trade.disclosure_date, func.count(Trade.id)).where(in_window).group_by(Trade.disclosure_date)
        ).all()
    )
    daily = [
        DailyCount(date=d, count=counts.get(d, 0))
        for d in (cutoff + timedelta(days=i) for i in range(days + 1))
    ]

    year, month = extract("year", Trade.disclosure_date), extract("month", Trade.disclosure_date)
    other = func.sum(case((Trade.transaction_type.in_(("buy", "sell", "sell_partial")), 0), else_=1))
    monthly_rows = session.execute(
        select(year, month, buys, sells, other).where(Trade.disclosure_date.is_not(None)).group_by(year, month).order_by(year, month)
    ).all()
    monthly = [
        MonthlyCount(month=f"{int(y):04d}-{int(m):02d}", buys=b or 0, sells=s_ or 0, other=o or 0)
        for y, m, b, s_, o in monthly_rows
    ]

    # The display name comes from the securities table. `max(trades.asset_name)` depended on the
    # database collation, so SQLite and PostgreSQL picked different names. Ties break on id, not on
    # text, for the same reason.
    top_tickers = [
        TopTicker(ticker=t, name=n, trades=c, buys=b or 0, sells=s_ or 0)
        for t, n, c, b, s_ in session.execute(
            select(Security.ticker, Security.name, func.count(Trade.id), buys, sells)
            .join(Trade, Trade.security_id == Security.id)
            .where(in_window)
            .group_by(Security.id)
            .order_by(func.count(Trade.id).desc(), Security.id)
            .limit(10)
        ).all()
    ]
    top_politicians = [
        TopPolitician(id=i, name=n, chamber=c, trades=cnt)
        for i, n, c, cnt in session.execute(
            select(Politician.id, Politician.name, Politician.chamber, func.count(Trade.id))
            .join(Trade, Trade.politician_id == Politician.id)
            .where(in_window)
            .group_by(Politician.id)
            .order_by(func.count(Trade.id).desc(), Politician.id)
            .limit(10)
        ).all()
    ]
    return OverviewOut(
        window_days=days,
        totals=OverviewTotals(
            trades=total_trades,
            politicians=session.scalar(select(func.count(Politician.id))) or 0,
            securities=session.scalar(select(func.count(Security.id))) or 0,
            trades_in_window=win_total or 0,
            buys_in_window=win_buys or 0,
            sells_in_window=win_sells or 0,
        ),
        latest_disclosure_date=session.scalar(select(func.max(Trade.disclosure_date))),
        daily=daily,
        monthly=monthly,
        top_tickers=top_tickers,
        top_politicians=top_politicians,
    )


@router.get("/status", response_model=StatusOut)
def data_status(session: Session = Depends(get_session)) -> StatusOut:
    today = date.today()
    bench = get_settings().benchmark_ticker
    bench_sec = session.scalar(select(Security).where(Security.ticker == bench))
    traded = Security.id.in_(select(Trade.security_id).where(Trade.security_id.is_not(None)))
    settings = get_settings()
    last_success = session.scalar(select(func.max(IngestState.last_success_at)))
    age_hours = (
        (datetime.now(UTC).replace(tzinfo=None) - last_success).total_seconds() / 3600 if last_success else None
    )
    by_source = dict(session.execute(select(Trade.source, func.count(Trade.id)).group_by(Trade.source)).all())
    return StatusOut(
        trades_total=sum(by_source.values()),
        trades_by_source=by_source,
        politicians_total=session.scalar(select(func.count(Politician.id))) or 0,
        latest_disclosure_date=session.scalar(select(func.max(Trade.disclosure_date))),
        latest_transaction_date=session.scalar(select(func.max(Trade.transaction_date)).where(Trade.transaction_date <= today)),
        last_ingested_at=session.scalar(select(func.max(Trade.created_at))),
        last_successful_ingest_at=last_success,
        ingest_age_hours=round(age_hours, 2) if age_hours is not None else None,
        ingest_stale_after_hours=settings.ingest_stale_after_hours,
        # Fresh data is not an error. Stale means "older than the threshold" or "never recorded".
        ingest_stale=age_hours is None or age_hours > settings.ingest_stale_after_hours,
        invalid_date_trades=session.scalar(
            select(func.count(Trade.id)).where(
                or_(Trade.transaction_date > today, Trade.transaction_date > Trade.disclosure_date)
            )
        ) or 0,
        securities_total=session.scalar(select(func.count(Security.id)).where(traded)) or 0,
        securities_priced=session.scalar(select(func.count(Security.id)).where(traded, Security.price_status == "ok")) or 0,
        securities_unavailable=session.scalar(
            select(func.count(Security.id)).where(traded, Security.price_status == "unavailable")
        ) or 0,
        securities_pending=session.scalar(select(func.count(Security.id)).where(traded, Security.price_status.is_(None))) or 0,
        price_bars=session.scalar(select(func.count()).select_from(PriceBar)) or 0,
        latest_bar_date=session.scalar(select(func.max(PriceBar.date))),
        benchmark_ticker=bench,
        benchmark_from=bench_sec.price_from if bench_sec else None,
        benchmark_to=bench_sec.price_to if bench_sec else None,
        benchmark_status=bench_sec.price_status if bench_sec else None,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="POLTRACKER", version="0.1.0")
    origins = settings.cors_origin_list
    if origins:  # an empty CORS_ORIGINS disables cross-origin access entirely
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET"],  # the API is read-only
            allow_headers=["Accept", "Content-Type"],
            allow_credentials=False,
            max_age=600,
        )
    from .personalization import router as personalization_router  # before `router`: /trades/screen must win over /trades/{trade_id}

    app.include_router(personalization_router)
    if settings.local_views_enabled:
        from .views import router as views_router

        app.include_router(views_router)
    app.include_router(router)
    return app


app = create_app()
