"""User-adjustable context rules: a personal screen over the STORED, objective trade context. Nothing here writes `trade_context`.

The deterministic engine (trade_context.py) stores objective facts per trade (committee relevance with its seat timing, the size percentile, the disclosure delay
and the 90-day excess return) and the canonical default result `flagged_for_contextual_review`. A `ContextRule` re-reads those stored facts under the user's own
thresholds and signal choices and says whether the trade matches the user's CUSTOM SCREEN. That match is a different thing from the canonical flag and is always
reported separately. The default rule reproduces the canonical methodology exactly: at a default threshold the rule uses the engine's own stored boolean for that
signal, so there is no re-derivation that could differ by rounding.

The rule is built once as SQL expressions over the `trade_context` columns, so the same definition filters the table on the server and labels each row.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, case, exists, false, func, or_, select, true

from .models import TradeContext, TradeContextEvidence
from .trade_context import ContextConfig, TEMPORALLY_VERIFIED

_D = ContextConfig()
DEFAULT_SIZE_PERCENTILE = _D.size_percentile
DEFAULT_DELAY_DAYS = _D.delay_days
DEFAULT_EXCESS_PP = round(_D.excess_return * 100, 6)
DEFAULT_MIN_SECONDARY = _D.min_secondary_signals
SECONDARY = ("trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal")

KIND_DEFAULT = "default"  # exactly the canonical methodology
KIND_CUSTOM = "custom"  # committee relevance and at least one secondary signal, with the user's choices
KIND_COMMITTEE_ONLY = "committee_only"  # committee relevance alone: for browsing, not the contextual-review flag
KIND_MARKET_ONLY = "market_only"  # market signals only: says nothing about political context


class ContextRule(BaseModel):
    """The user's personalization of how trades are screened. Defaults are the canonical production methodology."""

    model_config = ConfigDict(extra="forbid")

    committee_relevance_required: bool = True
    reviewed_direct_only: bool = True  # False also counts REVIEWED related (supporting) mappings as committee relevance; a needs_review mapping is never stored or used
    require_temporal_verification: bool = True  # committee evidence must be verified for the transaction date
    enable_trade_size_signal: bool = True
    trade_size_percentile_threshold: float = Field(DEFAULT_SIZE_PERCENTILE, ge=0, le=100)
    enable_disclosure_delay_signal: bool = True
    disclosure_delay_threshold_days: int = Field(DEFAULT_DELAY_DAYS, ge=0, le=3650)
    enable_excess_return_signal: bool = True
    excess_return_threshold_pct_points: float = Field(DEFAULT_EXCESS_PP, ge=0, le=1000)
    minimum_secondary_signals: int = Field(DEFAULT_MIN_SECONDARY, ge=0, le=3)

    @model_validator(mode="after")
    def _coherent(self) -> "ContextRule":
        enabled = self.enabled_secondary_count
        if self.minimum_secondary_signals > enabled:
            raise ValueError(f"minimum_secondary_signals ({self.minimum_secondary_signals}) is more than the {enabled} secondary signal(s) enabled; nothing could match")
        if not self.committee_relevance_required and self.minimum_secondary_signals < 1:
            raise ValueError("a rule that does not require committee relevance needs at least one secondary signal, otherwise it would match every trade")
        return self

    @property
    def enabled_secondary_count(self) -> int:
        return sum([self.enable_trade_size_signal, self.enable_disclosure_delay_signal, self.enable_excess_return_signal])

    def is_default(self) -> bool:
        return self == ContextRule()

    def kind(self) -> str:
        if self.is_default():
            return KIND_DEFAULT
        if not self.committee_relevance_required:
            return KIND_MARKET_ONLY
        if self.minimum_secondary_signals == 0:
            return KIND_COMMITTEE_ONLY
        return KIND_CUSTOM


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    kind: str
    description: str
    notes: tuple[str, ...]
    rule: ContextRule


PRESETS: dict[str, Preset] = {p.key: p for p in (
    Preset("balanced", "Balanced", KIND_DEFAULT,
           "The default POLTRACKER methodology: the same result as the stored contextual-review flag.",
           ("Committee relevance required (reviewed direct mapping, seat verified for the transaction date).",
            "Trade-size percentile >= 90, disclosure delay > 45 days, absolute 90-day excess return >= 20 percentage points.",
            "At least 2 of those 3 secondary signals."),
           ContextRule()),
    Preset("strict", "Strict", KIND_CUSTOM,
           "A narrower custom screen: all three secondary signals, at higher thresholds.",
           ("Committee relevance required, reviewed direct only, seat verified.",
            "Trade-size percentile >= 95, disclosure delay > 60 days, absolute 90-day excess return >= 25 percentage points.",
            "All 3 secondary signals."),
           ContextRule(trade_size_percentile_threshold=95, disclosure_delay_threshold_days=60, excess_return_threshold_pct_points=25, minimum_secondary_signals=3)),
    Preset("committee_focus", "Committee focus", KIND_COMMITTEE_ONLY,
           "For browsing trades by committee relevance alone. This is not the contextual-review flag.",
           ("Committee relevance required (reviewed direct mapping, seat verified).",
            "No secondary signal is required, so every committee-relevant trade matches.",
            "A match here only means the committee and industry line up; it is not a flag."),
           ContextRule(minimum_secondary_signals=0)),
    Preset("market_focus", "Market focus", KIND_MARKET_ONLY,
           "Trades with unusual size, a long disclosure delay or a large excess return. Says nothing about political context.",
           ("Committee relevance is not required or used.",
            "Trade-size percentile >= 90, disclosure delay > 45 days, absolute 90-day excess return >= 20 percentage points.",
            "At least 2 of those 3 signals. A match is a performance and filing-timing screen, not evidence about anyone."),
           ContextRule(committee_relevance_required=False)),
)}


KIND_LABEL = {
    KIND_DEFAULT: "Default methodology",
    KIND_CUSTOM: "Custom screen",
    KIND_COMMITTEE_ONLY: "Browsing by committee relevance (not the contextual-review flag)",
    KIND_MARKET_ONLY: "Market-signal screen (does not indicate political context)",
}


@dataclass(frozen=True)
class RuleExpressions:
    """SQL expressions over the stored trade_context row `C` (all NULL-safe booleans)."""

    committee_active: object
    size_active: object
    delay_active: object
    excess_active: object
    active_count: object  # active signals, committee included when it counts under the rule
    matches: object


def _flag(expr):
    return case((expr, 1), else_=0)


def rule_expressions(rule: ContextRule, C=TradeContext) -> RuleExpressions:
    related_exists = exists(select(1).where(
        TradeContextEvidence.trade_context_id == C.id, TradeContextEvidence.signal_type == "committee_relevance",
        TradeContextEvidence.evidence_type == "reviewed_related_mapping"))
    committee_ok = C.committee_relevance.is_(True)
    if not rule.reviewed_direct_only:
        committee_ok = or_(committee_ok, related_exists)
    committee_active = and_(committee_ok, C.committee_temporal_status == TEMPORALLY_VERIFIED) if rule.require_temporal_verification else committee_ok

    # At a default threshold use the engine's stored boolean (identical to the canonical decision); otherwise read the stored number.
    if not rule.enable_trade_size_signal:
        size = false()
    elif rule.trade_size_percentile_threshold == DEFAULT_SIZE_PERCENTILE:
        size = C.trade_size_anomaly.is_(True)
    else:
        size = and_(C.trade_size_percentile.is_not(None), C.trade_size_percentile >= rule.trade_size_percentile_threshold)
    if not rule.enable_disclosure_delay_signal:
        delay = false()
    elif rule.disclosure_delay_threshold_days == DEFAULT_DELAY_DAYS:
        delay = C.disclosure_delay_signal.is_(True)
    else:
        delay = and_(C.disclosure_delay_days.is_not(None), C.disclosure_delay_days > rule.disclosure_delay_threshold_days)
    if not rule.enable_excess_return_signal:
        excess = false()
    elif rule.excess_return_threshold_pct_points == DEFAULT_EXCESS_PP:
        excess = C.excess_return_signal.is_(True)
    else:
        excess = and_(C.performance_status == "ok", C.excess_return.is_not(None),
                      func.abs(C.excess_return) * 100 + 1e-7 >= rule.excess_return_threshold_pct_points)  # same float tolerance as the engine

    secondary_count = _flag(size) + _flag(delay) + _flag(excess)
    counts_committee = committee_active if rule.committee_relevance_required else false()
    active_count = secondary_count + (_flag(committee_active) if rule.committee_relevance_required else 0)
    matches = and_(counts_committee if rule.committee_relevance_required else true(), secondary_count >= rule.minimum_secondary_signals)
    return RuleExpressions(committee_active, size, delay, excess, active_count, matches)
