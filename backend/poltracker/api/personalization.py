"""Read-only personalization API: built-in presets and the server-side trade screen. GET only (the API's CORS policy is GET-only), and it never writes.

The screen applies the user's filters and context rule over the STORED trade context. `custom_screen` on each trade is the user's current rule, reported next to the
canonical `context.flagged_for_contextual_review`, which is never changed by it.
"""

import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..context_rules import KIND_LABEL, PRESETS, ContextRule, rule_expressions
from ..models import Trade, TradeContext
from ..trade_screen import MAX_FILTERS, FilterSpec, as_int, screen_statement
from .main import get_session
from .ordering import nulls_last, text_order
from .schemas import CustomScreenOut, PresetOut, PresetsOut, ScreenPageOut

router = APIRouter()

NOTICE = ("A custom screen re-reads stored, objective context under your own settings. It is not the contextual-review flag, and neither says anything about "
          "intent or knowledge.")


def _main():
    from . import main  # imported late: main registers this router

    return main


def preset_out(p) -> PresetOut:
    return PresetOut(key=p.key, label=p.label, kind=p.kind, description=p.description, notes=list(p.notes), rule=p.rule)


@router.get("/context/presets", response_model=PresetsOut)
def get_presets() -> PresetsOut:
    return PresetsOut(default_rule=ContextRule(), presets=[preset_out(p) for p in PRESETS.values()], kind_labels=KIND_LABEL, notice=NOTICE)


def parse_rule(raw: str | None) -> ContextRule:
    try:
        return ContextRule.model_validate_json(raw) if raw else ContextRule()
    except ValidationError as exc:
        raise HTTPException(422, f"rule: {exc.errors()[0]['msg']}") from exc


def parse_filters(raw: str | None) -> list[FilterSpec]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("filters must be a list")
        if len(data) > MAX_FILTERS:
            raise ValueError(f"at most {MAX_FILTERS} filters")
        return [FilterSpec.model_validate(item) for item in data]
    except ValidationError as exc:
        raise HTTPException(422, f"filters: {exc.errors()[0]['msg']}") from exc
    except ValueError as exc:
        raise HTTPException(422, f"filters: {exc}") from exc


@router.get("/trades/screen", response_model=ScreenPageOut)
def screen_trades(
    rule: str | None = Query(None, description="JSON ContextRule; omitted = the default methodology"),
    filters: str | None = Query(None, description="JSON list of {field, op, value}; combined with AND"),
    sort_by: Literal["transaction_date", "disclosure_date", "amount_min", "ticker", "politician_name"] = "disclosure_date",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ScreenPageOut:
    m = _main()
    rule_obj, specs = parse_rule(rule), parse_filters(filters)
    key = m._context_key(session)
    stmt, X = screen_statement(session, rule_obj, specs, key, Trade.id)
    sub = stmt.add_columns(as_int(X.matches).label("m"), as_int(TradeContext.flagged_for_contextual_review.is_(True)).label("f")).subquery()
    total, custom_count, canonical_count = session.execute(select(func.count(), func.coalesce(func.sum(sub.c.m), 0), func.coalesce(func.sum(sub.c.f), 0))).one()

    page_stmt, X = screen_statement(session, rule_obj, specs, key, Trade, as_int(X.committee_active).label("c"), as_int(X.size_active).label("s"),
                                    as_int(X.delay_active).label("d"), as_int(X.excess_active).label("e"), as_int(X.matches).label("m"),
                                    X.active_count.label("n"), TradeContext.id.label("ctx_id"), TradeContext.flagged_for_contextual_review.label("flag"))
    column = getattr(Trade, sort_by)
    if sort_by in ("ticker", "politician_name"):
        column = text_order(session, column)
    direction = nulls_last(column.asc() if order == "asc" else column.desc())
    rows = session.execute(page_stmt.order_by(direction, Trade.id.desc()).limit(limit).offset(offset)).all()
    outs = m._trade_outs(session, [r[0] for r in rows])
    kind = rule_obj.kind()
    for out, r in zip(outs, rows):
        if r.ctx_id is None:
            continue  # no stored context for this trade: nothing to screen
        active = [name for name, on in (("committee_relevance", rule_obj.committee_relevance_required and r.c), ("trade_size_anomaly", r.s),
                                         ("disclosure_delay_signal", r.d), ("excess_return_signal", r.e)) if on]
        out.custom_screen = CustomScreenOut(matches=bool(r.m), active_signals=active, active_signal_count=int(r.n), kind=kind, kind_label=KIND_LABEL[kind],
                                            canonical_flag=bool(r.flag), differs_from_canonical=bool(r.m) != bool(r.flag))
    return ScreenPageOut(items=outs, total=total or 0, limit=limit, offset=offset, rule=rule_obj, kind=kind, kind_label=KIND_LABEL[kind], is_default_rule=rule_obj.is_default(),
                         custom_match_count=int(custom_count), canonical_flag_count=int(canonical_count), notice=NOTICE)
