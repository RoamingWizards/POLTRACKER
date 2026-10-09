"""Server-side trade screening: AND-combined filters plus a user context rule, over stored data only (no network, no model).

Filters narrow the trades. The rule (context_rules.ContextRule) decides, per trade, whether it matches the user's custom screen; that is reported next to, never
instead of, the canonical `flagged_for_contextual_review`. Nothing here writes any table.
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import and_, case, exists, func, or_, select

from .context_rules import ContextRule, RuleExpressions, rule_expressions
from .models import CommitteeIndustryMapping, Politician, Security, Trade, TradeContext, TradeContextAnalysis, TradeContextEvidence
from .trade_context_llm import PROMPT_VERSION

FIELDS: dict[str, tuple[str, ...]] = {
    "politician": ("is", "contains"),
    "chamber": ("is",),
    "party": ("is",),
    "state": ("is",),
    "district": ("is",),
    "ticker": ("is", "contains"),
    "company": ("contains",),
    "industry": ("contains",),
    "transaction_type": ("is", "in"),
    "transaction_date": ("gte", "lte", "between"),
    "disclosure_date": ("gte", "lte", "between"),
    "value": ("gte", "lte"),  # the DISCLOSED range: gte -> the range's minimum is at least v; lte -> its maximum is at most v. Never a midpoint.
    "committee_relevance": ("is",),  # yes | no | unknown (the stored, default-methodology value)
    "committee_name": ("contains",),  # a committee or subcommittee in this trade's stored context evidence
    "trade_size_percentile": ("gte", "lte"),
    "disclosure_delay": ("gte", "lte"),  # days after the transaction
    "excess_return": ("abs_gte", "gte", "lte"),  # percentage points, 90 days from the transaction anchor, versus the benchmark
    "active_signals": ("gte", "lte", "eq"),  # signals active under the CURRENT rule
    "review_status": ("is",),  # flagged | not_flagged: the canonical default-methodology flag
    "custom_screen": ("is",),  # match | no_match: the current rule
    "ai_context": ("is",),  # available | unavailable
}
MAX_FILTERS = 25


class FilterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[tuple(FIELDS)]  # type: ignore[valid-type]
    op: str
    value: Any

    @model_validator(mode="after")
    def _check(self) -> "FilterSpec":
        if self.op not in FIELDS[self.field]:
            raise ValueError(f"filter {self.field!r} does not support {self.op!r} (use one of {', '.join(FIELDS[self.field])})")
        f, v = self.field, self.value
        if self.op == "between":
            if not (isinstance(v, (list, tuple)) and len(v) == 2):
                raise ValueError("between needs [start, end]")
            self.value = [_as_date(v[0]), _as_date(v[1])]
        elif f in ("transaction_date", "disclosure_date"):
            self.value = _as_date(v)
        elif self.op == "in":
            if not (isinstance(v, list) and v and all(isinstance(x, str) and x.strip() for x in v)):
                raise ValueError("in needs a non-empty list of strings")
            self.value = [x.strip() for x in v]
        elif f == "politician" and self.op == "is":
            self.value = _as_int(v)
        elif f in ("value", "trade_size_percentile", "disclosure_delay", "excess_return", "active_signals"):
            self.value = _as_number(v)
        elif f == "chamber":
            self._one_of(v, ("house", "senate"))
        elif f == "committee_relevance":
            self._one_of(v, ("yes", "no", "unknown"))
        elif f == "review_status":
            self._one_of(v, ("flagged", "not_flagged"))
        elif f == "custom_screen":
            self._one_of(v, ("match", "no_match"))
        elif f == "ai_context":
            self._one_of(v, ("available", "unavailable"))
        else:
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"{f} needs a non-empty text value")
            self.value = v.strip()
        return self

    def _one_of(self, v, options):
        if v not in options:
            raise ValueError(f"{self.field} must be one of {', '.join(options)}")


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError as exc:
        raise ValueError("dates must be YYYY-MM-DD") from exc


def _as_int(v) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, str)) or not str(v).lstrip("-").isdigit():
        raise ValueError("a whole number is needed")
    return int(v)


def _as_number(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise ValueError("a number is needed")
    try:
        return float(v)
    except ValueError as exc:
        raise ValueError("a number is needed") from exc


def _like(column, text: str):
    return column.ilike(f"%{text}%")


def _filter_clause(f: FilterSpec, X: RuleExpressions, session) -> Any:
    C, A, E = TradeContext, TradeContextAnalysis, TradeContextEvidence
    field, op, v = f.field, f.op, f.value
    if field == "politician":
        return Trade.politician_id == v if op == "is" else _like(Trade.politician_name, v)
    if field == "chamber":
        return Trade.chamber == v
    if field == "party":
        return func.lower(Trade.party) == v.lower()
    if field == "state":
        return func.upper(Trade.state) == v.upper()
    if field == "district":
        return Politician.district == v
    if field == "ticker":
        return Trade.ticker == v.upper() if op == "is" else _like(Trade.ticker, v)
    if field == "company":
        return or_(_like(Trade.asset_name, v), _like(Security.company_name, v), _like(Security.name, v))
    if field == "industry":
        return or_(_like(Security.industry, v), _like(Security.sector, v))
    if field == "transaction_type":
        return Trade.transaction_type == v if op == "is" else Trade.transaction_type.in_(v)
    if field in ("transaction_date", "disclosure_date"):
        col = Trade.transaction_date if field == "transaction_date" else Trade.disclosure_date
        return col >= v if op == "gte" else col <= v if op == "lte" else and_(col >= v[0], col <= v[1])
    if field == "value":
        return and_(Trade.amount_min.is_not(None), Trade.amount_min >= v) if op == "gte" else and_(Trade.amount_max.is_not(None), Trade.amount_max <= v)
    if field == "committee_relevance":
        return C.committee_relevance.is_(True) if v == "yes" else C.committee_relevance.is_(False) if v == "no" else and_(C.id.is_not(None), C.committee_relevance.is_(None))
    if field == "committee_name":
        codes = [r for (r,) in session.execute(select(CommitteeIndustryMapping.committee_code).where(_like(CommitteeIndustryMapping.committee_name, v)).distinct())]
        subs = [r for (r,) in session.execute(select(CommitteeIndustryMapping.subcommittee_code).where(
            CommitteeIndustryMapping.subcommittee_code.is_not(None), _like(CommitteeIndustryMapping.subcommittee_name, v)).distinct())]
        seat = or_(*(([E.committee_code.in_(codes)] if codes else []) + ([E.subcommittee_code.in_(subs)] if subs else []))) if (codes or subs) else None
        if seat is None:
            return Trade.id < 0  # no committee of that name exists: nothing matches
        return exists(select(1).where(E.trade_context_id == C.id, E.signal_type == "committee_relevance",
                                      E.evidence_type.in_(("reviewed_direct_mapping", "reviewed_related_mapping")), seat))
    if field == "trade_size_percentile":
        return and_(C.trade_size_percentile.is_not(None), C.trade_size_percentile >= v if op == "gte" else C.trade_size_percentile <= v)
    if field == "disclosure_delay":
        return and_(C.disclosure_delay_days.is_not(None), C.disclosure_delay_days >= v if op == "gte" else C.disclosure_delay_days <= v)
    if field == "excess_return":
        pp = C.excess_return * 100
        base = C.excess_return.is_not(None)
        return and_(base, func.abs(pp) + 1e-7 >= v) if op == "abs_gte" else and_(base, pp >= v) if op == "gte" else and_(base, pp <= v)
    if field == "active_signals":
        return and_(C.id.is_not(None), X.active_count >= v if op == "gte" else X.active_count <= v if op == "lte" else X.active_count == v)
    if field == "review_status":
        return C.flagged_for_contextual_review.is_(True) if v == "flagged" else C.flagged_for_contextual_review.is_(False)
    if field == "custom_screen":
        return and_(C.id.is_not(None), X.matches) if v == "match" else and_(C.id.is_not(None), ~X.matches)
    if field == "ai_context":
        has = exists(select(1).where(A.trade_id == Trade.id, A.context_version == C.context_version, A.mapping_version == C.mapping_version,
                                     A.prompt_version == PROMPT_VERSION, A.context_digest == C.result_digest))
        return and_(C.id.is_not(None), has) if v == "available" else and_(C.id.is_not(None), ~has)
    raise ValueError(field)  # unreachable: FilterSpec validates the field


def screen_statement(session, rule: ContextRule, filters: list[FilterSpec], key: tuple[str, str | None] | None, *columns):
    """SELECT <Trade, extra columns...> with the context row joined for the current context key, and every filter ANDed on."""
    X = rule_expressions(rule)
    C = TradeContext
    join = and_(C.trade_id == Trade.id, C.context_version == (key[0] if key else None), C.mapping_version == (key[1] if key else None))
    stmt = (select(*columns or (Trade,)).select_from(Trade).outerjoin(C, join)
            .outerjoin(Politician, Politician.id == Trade.politician_id).outerjoin(Security, Security.id == Trade.security_id))
    for f in filters:
        stmt = stmt.where(_filter_clause(f, X, session))
    return stmt, X


def as_int(expr):
    return case((expr, 1), else_=0)
