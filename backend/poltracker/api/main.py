from collections import Counter
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import make_session_factory
from ..models import IngestState, PriceBar, Politician, Security, Trade
from ..performance import load_benchmark, load_series, trade_performance
from .ordering import nulls_last, text_order
from .schemas import (
    DailyCount,
    MonthlyCount,
    OverviewOut,
    OverviewTotals,
    StatusOut,
    TopPolitician,
    TopTicker,
    PoliticianOut,
    PoliticianPageOut,
    PriceSeriesOut,
    SecurityOut,
    SecurityPerformanceOut,
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
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/trades", response_model=TradePageOut)
def list_trades(
    ticker: str | None = None,
    politician_id: int | None = None,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    transaction_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = getattr(Trade, sort_by)
    if sort_by in ("ticker", "politician_name"):
        column = text_order(session, column)
    direction = nulls_last(column.asc() if order == "asc" else column.desc())
    rows = session.scalars(stmt.order_by(direction, Trade.id.desc()).limit(limit).offset(offset)).all()
    return TradePageOut(items=rows, total=total, limit=limit, offset=offset)


@router.get("/trades/{trade_id}", response_model=TradeOut)
def get_trade(trade_id: int, session: Session = Depends(get_session)) -> Trade:
    trade = session.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(404, "Trade not found")
    return trade


def _politician_out(session: Session, pol: Politician) -> PoliticianOut:
    count, latest = session.execute(
        select(func.count(Trade.id), func.max(Trade.transaction_date)).where(Trade.politician_id == pol.id)
    ).one()
    return PoliticianOut(
        id=pol.id, name=pol.name, chamber=pol.chamber, party=pol.party, state=pol.state,
        trade_count=count, latest_trade_date=latest,
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


@router.get("/politicians/{politician_id}", response_model=PoliticianOut)
def get_politician(politician_id: int, session: Session = Depends(get_session)) -> PoliticianOut:
    pol = session.get(Politician, politician_id)
    if pol is None:
        raise HTTPException(404, "Politician not found")
    return _politician_out(session, pol)


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
    app.include_router(router)
    return app


app = create_app()
