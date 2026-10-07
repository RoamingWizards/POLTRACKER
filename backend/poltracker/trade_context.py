"""Deterministic trade context signals. Public data only: no network, no language model, no scoring.

Four signals, each True, False or None (unknown):

  committee_relevance      a REVIEWED + DIRECT committee/industry mapping applies to the politician's seats and the security's SIC code
  trade_size_anomaly       the trade's disclosed range is unusually large for this politician's own earlier trades
  disclosure_delay_signal  the disclosure came at least `delay_days` after the transaction
  excess_return_signal     the security's return since the trade differs from the benchmark's by at least `excess_return`

A trade is flagged for contextual review only when committee_relevance is True AND at least one secondary signal is True. Performance, size
or delay alone never flag a trade. A flag is a prompt for a person to look at public context, not a finding of any kind: nothing here
estimates the probability of improper conduct or says a member knew anything.

Methodology (version `ENGINE_VERSION`)

* Trade size. Disclosures give a range, never an exact amount. The representative value is the range midpoint for a closed range, the
  lower bound for an open-ended top range ("Over $50,000,000", which can only understate), and the figure itself when min == max. A trade
  with no usable range is unknown. The percentile is the mid-rank among the same politician's trades with a strictly EARLIER transaction
  date (ties count half), so a politician whose earlier trades all share one range never looks unusual, history is stable as new trades arrive,
  and nothing is compared across politicians. Fewer than `min_history` earlier trades with a usable range gives unknown.
* Disclosure delay. disclosure_date - transaction_date in days. A missing, future or inconsistent date (including a negative delay) is
  unknown; the source date is never repaired.
* Excess return. The existing performance engine over a FIXED horizon (default 90 days) from the transaction-date anchor, security return minus
  the benchmark's. A fixed window keeps trades comparable: measured to the latest bar, a year-old trade needs far less luck to exceed 10 points
  than a month-old one. A trade younger than the horizon, or whose prices stop sooner, is unknown. The signal uses the absolute raw value; the
  direction-adjusted figure is stored separately.
* Committee relevance uses the politician's CURRENT committee seats, as published by the House Clerk, even for older trades: seat history is not
  available, so a member may not have held a seat when an older trade was made.
"""

import hashlib
import json
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass, field
from datetime import date

from .committee_industry import Assignment, CommitteeIndustryMatcher, Match
from .performance import PriceSeries, TradePerformance, compute_performance, transaction_date_problem

ENGINE_VERSION = "2026.1"

SIGNALS = ("committee_relevance", "trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal")
SECONDARY = ("trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal")
NOTICE = ("Context indicators are derived from public data and do not establish that a member possessed or acted on material non-public information.")


@dataclass(frozen=True)
class ContextConfig:
    delay_days: int = 30  # disclosure_delay_signal when the delay is at least this many days
    excess_return: float = 0.10  # excess_return_signal when |excess return| is at least this (0.10 = 10 percentage points)
    size_percentile: float = 90.0  # trade_size_anomaly when the percentile is at least this
    excess_horizon_days: int = 90  # measure from the transaction anchor to this many days later; a trade younger than this is unknown
    min_history: int = 10  # earlier trades with a usable range needed before a size percentile means anything
    benchmark: str = "SPY"

    def version_label(self) -> str:
        """The default configuration is the plain engine version; any other configuration gets its own label so it never overwrites default rows."""
        if self == ContextConfig():
            return ENGINE_VERSION
        digest = hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()[:6]
        return f"{ENGINE_VERSION}+custom-{digest}"


# --- trade size ---------------------------------------------------------------------------------------------------

def trade_size_value(amount_min: int | None, amount_max: int | None) -> tuple[float | None, str | None]:
    """A representative number for a disclosed range, and how it was derived. Never an exact transaction value."""
    if amount_min is None:
        return None, None  # a lone upper bound gives no defensible representative value
    if amount_max is None:
        return float(amount_min), "open_ended_lower_bound"
    if amount_max < amount_min:
        return None, None  # malformed range: not guessed at
    if amount_max == amount_min:
        return float(amount_min), "exact_figure"
    return (amount_min + amount_max) / 2, "range_midpoint"


def percentile_rank(value: float, prior_sorted: list[float]) -> float:
    """Mid-rank percentile (0-100) of `value` among `prior_sorted`; equal values count half."""
    n = len(prior_sorted)
    less = bisect_left(prior_sorted, value)
    equal = bisect_right(prior_sorted, value) - less
    return (less + 0.5 * equal) / n * 100


def median(sorted_values: list[float]) -> float | None:
    n = len(sorted_values)
    if not n:
        return None
    mid = n // 2
    return sorted_values[mid] if n % 2 else (sorted_values[mid - 1] + sorted_values[mid]) / 2


@dataclass
class SizeResult:
    anomaly: bool | None
    value: float | None = None
    basis: str | None = None
    percentile: float | None = None
    sample_size: int | None = None
    median: float | None = None


def size_signal(amount_min: int | None, amount_max: int | None, prior_sorted: list[float], cfg: ContextConfig, date_ok: bool = True) -> SizeResult:
    value, basis = trade_size_value(amount_min, amount_max)
    if value is None or not date_ok:
        return SizeResult(None, value, basis, sample_size=len(prior_sorted) if date_ok else None)
    n = len(prior_sorted)
    if n < cfg.min_history:
        return SizeResult(None, value, basis, sample_size=n, median=median(prior_sorted))
    pct = percentile_rank(value, prior_sorted)
    return SizeResult(pct >= cfg.size_percentile, value, basis, round(pct, 2), n, median(prior_sorted))


# --- disclosure delay ---------------------------------------------------------------------------------------------

def delay_signal(transaction_date: date, disclosure_date: date | None, today: date, cfg: ContextConfig) -> tuple[int | None, bool | None]:
    if disclosure_date is None or transaction_date_problem(transaction_date, disclosure_date, today) or disclosure_date > today:
        return None, None
    days = (disclosure_date - transaction_date).days
    return days, days >= cfg.delay_days


# --- excess return ------------------------------------------------------------------------------------------------

def excess_signal(perf: TradePerformance, cfg: ContextConfig) -> bool | None:
    leg = perf.transaction
    if perf.status != "ok" or leg is None or leg.excess_return is None:
        return None
    return abs(leg.excess_return) + 1e-9 >= cfg.excess_return  # tolerance: 0.10 must not be missed by float noise


# --- committee relevance ------------------------------------------------------------------------------------------

@dataclass
class CommitteeResult:
    value: bool | None
    reason: str
    direct: list[Match] = field(default_factory=list)  # reviewed + direct: the evidence for a True signal
    related: list[Match] = field(default_factory=list)  # reviewed + related: supporting context only
    pending_review: int = 0  # needs_review matches that were deliberately ignored


def committee_signal(matcher: CommitteeIndustryMatcher, assignments: list[Assignment], sic_code: object, industry: str | None) -> CommitteeResult:
    rel = matcher.evaluate(assignments, sic_code, industry)
    if rel.reason in ("no_sic", "no_committee_assignments"):
        return CommitteeResult(None, rel.reason)
    reviewed = [m for m in rel.matches if m.reviewed and m.review_status == "reviewed"]
    direct = [m for m in reviewed if m.level == "direct"]
    related = [m for m in reviewed if m.level == "related"]
    pending = sum(1 for m in rel.matches if not (m.reviewed and m.review_status == "reviewed"))
    if direct:
        return CommitteeResult(True, "direct_match", direct, related, pending)
    if rel.unmapped_committees:  # a committee with no mapping could still be relevant, so "no" cannot be asserted
        return CommitteeResult(None, "unmapped_committees", [], related, pending)
    return CommitteeResult(False, "no_reviewed_direct_match", [], related, pending)


# --- the flag ----------------------------------------------------------------------------------------------------

def is_flagged(committee: bool | None, size: bool | None, delay: bool | None, excess: bool | None) -> bool:
    """Committee relevance is mandatory; one secondary signal then completes the flag. Unknown never counts as True."""
    return committee is True and any(s is True for s in (size, delay, excess))


def signal_count(*signals: bool | None) -> int:
    return sum(1 for s in signals if s is True)


# --- one trade -----------------------------------------------------------------------------------------------------

@dataclass
class TradeInput:
    id: int
    politician_id: int
    ticker: str | None
    transaction_type: str
    transaction_date: date
    disclosure_date: date | None
    amount_min: int | None
    amount_max: int | None
    sic_code: str | None
    industry: str | None


@dataclass
class EvidenceItem:
    signal_type: str
    evidence_type: str
    evidence_key: str
    description: str
    committee_code: str | None = None
    subcommittee_code: str | None = None
    mapping_id: int | None = None
    source_url: str | None = None
    metadata: dict | None = None


@dataclass
class ContextResult:
    trade_id: int
    committee: CommitteeResult
    size: SizeResult
    delay_days: int | None
    delay: bool | None
    perf: TradePerformance
    excess: bool | None
    evidence: list[EvidenceItem]
    mapping_version: str | None

    @property
    def flagged(self) -> bool:
        return is_flagged(self.committee.value, self.size.anomaly, self.delay, self.excess)

    @property
    def count(self) -> int:
        return signal_count(self.committee.value, self.size.anomaly, self.delay, self.excess)

    def digest(self, version: str) -> str:
        """Stable hash of everything stored for the trade, so an unchanged result is recognised on rerun."""
        leg = self.perf.transaction
        payload = {
            "v": version, "m": self.mapping_version, "c": [self.committee.value, self.committee.reason],
            "size": [self.size.anomaly, self.size.value, self.size.basis, self.size.percentile, self.size.sample_size, self.size.median],
            "delay": [self.delay_days, self.delay],
            "perf": [self.perf.status, leg.return_ if leg else None, leg.benchmark_return if leg else None, leg.excess_return if leg else None,
                     str(leg.anchor_date) if leg else None, self.perf.direction_adjusted.get("transaction_excess_return")],
            "excess": self.excess,
            "evidence": [[e.signal_type, e.evidence_type, e.evidence_key, e.description, e.source_url, e.metadata] for e in self.evidence],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _money(v: float | None) -> str:
    return "n/a" if v is None else f"${v:,.0f}"


def _mapping_evidence(m: Match, kind: str, trade: TradeInput) -> EvidenceItem:
    where = m.committee_name + (f" / {m.subcommittee_name}" if m.subcommittee_name else "")
    label = "Direct" if kind == "reviewed_direct_mapping" else "Related (supporting context only)"
    return EvidenceItem(
        "committee_relevance", kind, f"mapping:{m.mapping_id}",
        f"{label}: {where}, SIC {m.sic_range}. {m.rationale}",
        m.committee_code, m.subcommittee_code, m.mapping_id, m.source_url,
        {"committee_name": m.committee_name, "subcommittee_name": m.subcommittee_name, "scope": m.scope, "sic_range": m.sic_range, "level": m.level,
         "review_status": m.review_status, "jurisdiction_basis": m.jurisdiction_basis, "mapping_version": m.mapping_version,
         "source_citation": m.source_citation, "security_sic_code": trade.sic_code, "security_industry": trade.industry},
    )


def analyze_trade(
    trade: TradeInput,
    *,
    matcher: CommitteeIndustryMatcher,
    assignments: list[Assignment],
    prior_sizes_sorted: list[float],
    series: PriceSeries | None,
    benchmark: PriceSeries | None,
    cfg: ContextConfig,
    today: date,
) -> ContextResult:
    committee = committee_signal(matcher, assignments, trade.sic_code, trade.industry)
    date_ok = transaction_date_problem(trade.transaction_date, trade.disclosure_date, today) is None
    size = size_signal(trade.amount_min, trade.amount_max, prior_sizes_sorted, cfg, date_ok)
    days, delay = delay_signal(trade.transaction_date, trade.disclosure_date, today, cfg)
    perf = compute_performance(
        ticker=trade.ticker, transaction_type=trade.transaction_type, transaction_date=trade.transaction_date,
        disclosure_date=trade.disclosure_date, series=series, benchmark=benchmark, benchmark_ticker=cfg.benchmark, today=today, horizon_days=cfg.excess_horizon_days,
    )
    excess = excess_signal(perf, cfg)

    evidence = [_mapping_evidence(m, "reviewed_direct_mapping", trade) for m in committee.direct]
    evidence += [_mapping_evidence(m, "reviewed_related_mapping", trade) for m in committee.related]
    if size.value is not None:
        text = f"Representative value {_money(size.value)} ({size.basis.replace('_', ' ')}) from the disclosed range {_money(trade.amount_min)}-{_money(trade.amount_max) if trade.amount_max is not None else 'open-ended'}."
        if size.percentile is not None:
            text += f" {size.percentile:.0f}th percentile among {size.sample_size} earlier trades by this politician (median {_money(size.median)})."
        else:
            text += f" Not enough history for a percentile: {size.sample_size or 0} earlier trades with a usable range, {cfg.min_history} needed."
        evidence.append(EvidenceItem("trade_size_anomaly", "metric", "metric", text, metadata={
            "value": size.value, "basis": size.basis, "percentile": size.percentile, "sample_size": size.sample_size, "median": size.median,
            "threshold_percentile": cfg.size_percentile, "min_history": cfg.min_history}))
    if days is not None:
        evidence.append(EvidenceItem("disclosure_delay_signal", "metric", "metric",
                                     f"Disclosed {days} days after the transaction (threshold {cfg.delay_days} days).",
                                     metadata={"days": days, "threshold_days": cfg.delay_days}))
    leg = perf.transaction
    if leg is not None and leg.excess_return is not None:
        evidence.append(EvidenceItem("excess_return_signal", "metric", "metric",
                                     f"{perf.benchmark or cfg.benchmark} excess return {leg.excess_return * 100:+.1f} percentage points over {cfg.excess_horizon_days} days from {leg.anchor_date} "
                                     f"(security {leg.return_ * 100:+.1f}%, benchmark {leg.benchmark_return * 100:+.1f}%; threshold {cfg.excess_return * 100:.0f} points, absolute).",
                                     metadata={"security_return": leg.return_, "benchmark_return": leg.benchmark_return, "excess_return": leg.excess_return,
                                               "anchor_date": str(leg.anchor_date), "horizon_days": cfg.excess_horizon_days,
                                               "direction_adjusted_excess_return": perf.direction_adjusted.get("transaction_excess_return"),
                                               "threshold": cfg.excess_return}))
    return ContextResult(trade.id, committee, size, days, delay, perf, excess, evidence, matcher.version)
