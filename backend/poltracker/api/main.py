from collections.abc import Iterator
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import make_session_factory
from ..models import Politician, Security, Trade
from .schemas import PoliticianOut, PoliticianPageOut, SecurityOut, TradeOut, TradePageOut

app = FastAPI(title="POLTRACKER", version="0.1.0")

_session_factory = None


def get_session() -> Iterator[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory()
    with _session_factory() as session:
        yield session


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/trades", response_model=TradePageOut)
def list_trades(
    ticker: str | None = None,
    politician_id: int | None = None,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    transaction_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
    rows = session.scalars(
        stmt.order_by(Trade.disclosure_date.desc(), Trade.id.desc()).limit(limit).offset(offset)
    ).all()
    return TradePageOut(items=rows, total=total, limit=limit, offset=offset)


@app.get("/trades/{trade_id}", response_model=TradeOut)
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


@app.get("/politicians", response_model=PoliticianPageOut)
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
    pols = session.scalars(stmt.order_by(Politician.name).limit(limit).offset(offset)).all()
    return PoliticianPageOut(items=[_politician_out(session, p) for p in pols], total=total, limit=limit, offset=offset)


@app.get("/politicians/{politician_id}", response_model=PoliticianOut)
def get_politician(politician_id: int, session: Session = Depends(get_session)) -> PoliticianOut:
    pol = session.get(Politician, politician_id)
    if pol is None:
        raise HTTPException(404, "Politician not found")
    return _politician_out(session, pol)


@app.get("/securities/{ticker}", response_model=SecurityOut)
def get_security(ticker: str, session: Session = Depends(get_session)) -> SecurityOut:
    sec = session.scalar(select(Security).where(Security.ticker == ticker.upper()))
    if sec is None:
        raise HTTPException(404, "Security not found")
    count, latest = session.execute(
        select(func.count(Trade.id), func.max(Trade.transaction_date)).where(Trade.security_id == sec.id)
    ).one()
    recent = session.scalars(
        select(Trade).where(Trade.security_id == sec.id).order_by(Trade.disclosure_date.desc(), Trade.id.desc()).limit(10)
    ).all()
    return SecurityOut(id=sec.id, ticker=sec.ticker, name=sec.name, trade_count=count, latest_trade_date=latest, recent_trades=recent)
