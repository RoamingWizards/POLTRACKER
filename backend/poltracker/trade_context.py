"""Deterministic trade context signals. Public data only: no network, no language model, no scoring.

Four signals, each True, False or None (unknown):

  committee_relevance      a REVIEWED + DIRECT committee/industry mapping applies to the politician's seats and the security's SIC code
  trade_size_anomaly       the trade's disclosed range is unusually large for this politician's own earlier trades
  disclosure_delay_signal  the disclosure came MORE than `delay_days` after the transaction
  excess_return_signal     the security's 90-day return after the trade differs from the benchmark's by at least `excess_return`

A trade is flagged for contextual review only when committee_relevance is True, at least `min_secondary_signals` (default two) of the three other signals are
True, AND the committee evidence is temporally verified (see below). Performance, size or delay alone never flag a trade. A flag is a prompt for a person
to look at public context, not a finding of any kind: nothing here estimates the probability of improper conduct or says a member knew anything.

Methodology (version `ENGINE_VERSION`)

* Trade size. Disclosures give a range, never an exact amount. The representative value is the range midpoint for a closed range, the lower bound for an
  open-ended top range ("Over $50,000,000", which can only understate), and the figure itself when min == max. A trade with no usable range is unknown.
  The percentile is the mid-rank among the same politician's trades with a strictly EARLIER transaction date (ties count half), so a politician whose
  earlier trades all share one range never looks unusual, history is stable as new trades arrive, and nothing is compared across politicians. Fewer than
  `min_history` earlier trades with a usable range gives unknown.
* Disclosure delay. disclosure_date - transaction_date in days; the raw number is always kept. A periodic transaction report is generally due by the earlier of
  30 days after the filer became aware of the transaction and 45 days after it. The awareness date is not public, so the transaction date is the only reference
  POLTRACKER has: the signal marks a delay of MORE than 45 days and says nothing about whether a filing was late, excused or improper, because the filing
  circumstances are unknown. A missing, future or inconsistent date (including a negative delay) is unknown; source dates are never repaired.
* Excess return. The existing performance engine over a FIXED 90-calendar-day horizon from the transaction-date anchor, security return minus the
  benchmark's. A fixed window keeps trades comparable and stops the age of a trade from driving the signal: measured to the latest bar, a year-old trade
  accumulates months of extra performance and needs far less luck to exceed a threshold than a recent one. A trade younger than the horizon, or whose prices
  stop sooner, is unknown. The signal uses the absolute raw value (default 20 percentage points); the direction-adjusted figure is stored separately.
* Committee seats and time. The House Clerk's snapshot (MemberData.xml) lists seats held NOW and has no dates, so on its own it can only show a seat exists
  today. Dated history comes from adopted House resolutions (committee_history.py: exact start and end dates, committee level only). Each piece of committee
  evidence carries a temporal status:
    temporally_verified     official records establish the seat on the transaction date (for a committee-level mapping)
    current_assignment_only the seat is known only from the current snapshot (always the case for a subcommittee seat, whose history is not recorded)
    unavailable             no committee data for the member (for example the Senate)
    contradicted            a current seat would match, but the official record shows the member did not hold it on the transaction date; the trade is not
                            committee-relevant and the rejected match is kept as evidence
  The underlying match is kept as contextual information, but only temporally_verified committee evidence can produce a flag. A verified committee seat never
  promotes a subcommittee-only match. Dates are never invented, and no third-party committee history is used.
"""

import hashlib
import json
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass, field
from datetime import date

from .committee_industry import Assignment, CommitteeIndustryMatcher, Match
from .committee_history import PRECISION_CONGRESS, PRECISION_EXACT, congress_of
from .performance import PriceSeries, TradePerformance, compute_performance, transaction_date_problem

ENGINE_VERSION = "2026.3"  # 2026.3: committee evidence uses dated seat history (verified / contradicted); 2026.2: 45-day delay, 20-point excess, two secondaries, temporal gate

SIGNALS = ("committee_relevance", "trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal")
SECONDARY = ("trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal")
NOTICE = ("Context indicators are derived from public data and do not establish that a member possessed or acted on material non-public information.")


TEMPORALLY_VERIFIED = "temporally_verified"
CURRENT_ASSIGNMENT_ONLY = "current_assignment_only"
UNAVAILABLE = "unavailable"
CONTRADICTED = "contradicted"  # a current seat would match, but official House records show the member did not hold it on the transaction date


@dataclass(frozen=True)
class ContextConfig:
    delay_days: int = 45  # disclosure_delay_signal when the delay EXCEEDS this many days (45 days after the transaction is the PTR reference point)
    excess_return: float = 0.20  # excess_return_signal when |excess return| is at least this (0.20 = 20 percentage points)
    size_percentile: float = 90.0  # trade_size_anomaly when the percentile is at least this
    excess_horizon_days: int = 90  # measure from the transaction anchor to this many calendar days later; a trade younger than this is unknown
    min_history: int = 10  # earlier trades with a usable range needed before a size percentile means anything
    min_secondary_signals: int = 2  # how many of size / delay / excess must be True (with committee relevance) to meet the flag rule
    require_temporal_verification: bool = True  # only temporally verified committee evidence can flag; False exists for what-if comparisons
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
    return days, days > cfg.delay_days


# --- excess return ------------------------------------------------------------------------------------------------

def excess_signal(perf: TradePerformance, cfg: ContextConfig) -> bool | None:
    leg = perf.transaction
    if perf.status != "ok" or leg is None or leg.excess_return is None:
        return None
    return abs(leg.excess_return) + 1e-9 >= cfg.excess_return  # tolerance: 0.10 must not be missed by float noise


# --- committee relevance ------------------------------------------------------------------------------------------

def _covers(seat: Assignment, d: date) -> bool:
    """Is the seat established on a date? An open-ended exact-date seat is only confirmed up to `verified_through`."""
    if seat.temporal_precision == PRECISION_CONGRESS:
        return seat.congress_number == congress_of(d)
    if seat.temporal_precision != PRECISION_EXACT or seat.start_date is None or d < seat.start_date:
        return False
    if seat.end_date is not None:
        return d <= seat.end_date
    return seat.verified_through is not None and d <= seat.verified_through


def committee_history_status(rows: list[Assignment], d: date, scanned: bool = False, snapshot_congress: int | None = None) -> str:
    """verified | contradicted | unknown for ONE committee's full-committee seats on a date, from dated (official-record) rows only.

    `scanned`: the official resolutions of that date's Congress were read for this member (they have complete dated seats there). Then the absence of this committee
    from them is evidence the member did not hold it, but only for a Congress other than the snapshot's own, where the snapshot would be the conflicting record."""
    n = congress_of(d)
    dated = [a for a in rows if a.temporal_precision in (PRECISION_EXACT, PRECISION_CONGRESS) and a.congress_number == n and not a.subcommittee_code]
    if not dated:
        return "contradicted" if scanned and snapshot_congress is not None and n != snapshot_congress else "unknown"
    exact = [a for a in dated if a.temporal_precision == PRECISION_EXACT and a.start_date]
    if any(_covers(a, d) for a in exact):
        return "verified"
    # Absence is only claimed from a complete scan: not yet elected, between two stints, or after a removal. A seat still open past its confirmation is unknown, not absent.
    absent = all(d < a.start_date or (a.end_date is not None and d > a.end_date) for a in exact)
    if exact and absent and all(a.history_complete for a in exact):
        return "contradicted"  # contradictory exact information outweighs a whole-Congress claim
    return "verified" if any(_covers(a, d) for a in dated if a.temporal_precision == PRECISION_CONGRESS) else "unknown"


def effective_seats(assignments: list[Assignment], d: date) -> list[tuple[Assignment, str]]:
    """The seats that can apply on a date, each with how well that is established. A seat the official record shows was not held is dropped, along with
    the subcommittee seats under it. Subcommittee seats have no dated history, so they are never better than current_assignment_only."""
    by_committee: dict[str, list[Assignment]] = {}
    for a in assignments:
        by_committee.setdefault(a.committee_code, []).append(a)
    n = congress_of(d)
    scanned = any(a.temporal_precision == PRECISION_EXACT and a.history_complete and a.congress_number == n for a in assignments)
    snapshot_congress = max((a.congress_number for a in assignments if a.temporal_precision == "current_snapshot" and a.congress_number), default=None)
    out: list[tuple[Assignment, str]] = []
    for code, rows in by_committee.items():
        status = committee_history_status(rows, d, scanned, snapshot_congress)
        if status == "contradicted":
            continue
        for a in rows:
            dated = a.temporal_precision in (PRECISION_EXACT, PRECISION_CONGRESS)
            if dated:
                if _covers(a, d):
                    out.append((a, TEMPORALLY_VERIFIED))
            elif a.subcommittee_code:
                out.append((a, CURRENT_ASSIGNMENT_ONLY))
            else:
                out.append((a, TEMPORALLY_VERIFIED if status == "verified" else CURRENT_ASSIGNMENT_ONLY))
    return out


@dataclass
class CommitteeResult:
    value: bool | None
    reason: str
    direct: list[Match] = field(default_factory=list)  # reviewed + direct: the evidence for a True signal
    related: list[Match] = field(default_factory=list)  # reviewed + related: supporting context only
    pending_review: int = 0  # needs_review matches that were deliberately ignored
    temporal_status: str = UNAVAILABLE
    evidence_status: dict[int, str] = field(default_factory=dict)  # mapping_id -> temporal status of the seat behind it
    contradicted: bool = False
    rejected: list[Match] = field(default_factory=list)  # direct matches a CURRENT seat would give that the official record shows did not apply


def _mapping_status(m: Match, seats: list[tuple[Assignment, str]]) -> str:
    """The best temporal status among the seats that make a mapping apply. A committee-level mapping is satisfied by a seat on the committee; a
    subcommittee mapping only by a seat on that subcommittee, so a verified committee seat never promotes a subcommittee match."""
    found = [st for a, st in seats if a.committee_code == m.committee_code and (m.subcommittee_code is None or a.subcommittee_code == m.subcommittee_code)]
    return TEMPORALLY_VERIFIED if TEMPORALLY_VERIFIED in found else CURRENT_ASSIGNMENT_ONLY


def committee_signal(matcher: CommitteeIndustryMatcher, assignments: list[Assignment], sic_code: object, industry: str | None,
                     transaction_date: date | None = None) -> CommitteeResult:
    seats = effective_seats(assignments, transaction_date) if transaction_date else [(a, CURRENT_ASSIGNMENT_ONLY) for a in assignments]
    rel = matcher.evaluate([a for a, _ in seats], sic_code, industry)
    if rel.reason == "no_sic":
        return CommitteeResult(None, "no_sic", temporal_status=UNAVAILABLE if not assignments else _overall(seats))
    if not assignments:
        return CommitteeResult(None, "no_committee_assignments", temporal_status=UNAVAILABLE)
    reviewed = [m for m in rel.matches if m.reviewed and m.review_status == "reviewed"]
    direct = [m for m in reviewed if m.level == "direct"]
    related = [m for m in reviewed if m.level == "related"]
    pending = sum(1 for m in rel.matches if not (m.reviewed and m.review_status == "reviewed"))
    status = {m.mapping_id: _mapping_status(m, seats) for m in direct + related}
    if direct:
        verified = any(status[m.mapping_id] == TEMPORALLY_VERIFIED for m in direct)
        return CommitteeResult(True, "direct_match", direct, related, pending, TEMPORALLY_VERIFIED if verified else CURRENT_ASSIGNMENT_ONLY, status)
    # No direct match on the seats that applied that day. Would the member's CURRENT seats have given one? Then the official record rejected it.
    rejected: list[Match] = []
    if transaction_date is not None and len(seats) < len(assignments):
        current_seats = [a for a in assignments if a.temporal_precision in (None, "current_snapshot")]  # what a snapshot-only reading would have used
        current = matcher.evaluate(current_seats, sic_code, industry)
        rejected = [m for m in current.matches if m.reviewed and m.review_status == "reviewed" and m.level == "direct"]
    if rejected:
        return CommitteeResult(False, "seat_not_held_on_transaction_date", [], related, pending, CONTRADICTED, status, True, rejected)
    if not seats:  # every seat was shown not to apply on the transaction date
        return CommitteeResult(False, "no_seat_on_transaction_date", [], [], 0, TEMPORALLY_VERIFIED)
    if rel.unmapped_committees:  # a committee with no mapping could still be relevant, so "no" cannot be asserted
        return CommitteeResult(None, "unmapped_committees", [], related, pending, _overall(seats), status)
    return CommitteeResult(False, "no_reviewed_direct_match", [], related, pending, _overall(seats), status)


def _overall(seats: list[tuple[Assignment, str]]) -> str:
    return TEMPORALLY_VERIFIED if seats and all(st == TEMPORALLY_VERIFIED for _, st in seats) else CURRENT_ASSIGNMENT_ONLY


# --- the flag ----------------------------------------------------------------------------------------------------

def secondary_count(size: bool | None, delay: bool | None, excess: bool | None) -> int:
    return sum(1 for s in (size, delay, excess) if s is True)


def meets_flag_rule(committee: bool | None, size: bool | None, delay: bool | None, excess: bool | None, min_secondary: int = 2) -> bool:
    """The context rule: committee relevance is mandatory, then enough secondary signals. Unknown never counts as True."""
    return committee is True and secondary_count(size, delay, excess) >= min_secondary


def is_flagged(committee: bool | None, size: bool | None, delay: bool | None, excess: bool | None, min_secondary: int = 2,
               temporal_status: str | None = TEMPORALLY_VERIFIED, require_temporal: bool = True) -> bool:
    """The rule is met AND (unless waived for a what-if) the committee evidence is temporally verified."""
    return meets_flag_rule(committee, size, delay, excess, min_secondary) and (not require_temporal or temporal_status == TEMPORALLY_VERIFIED)


def signal_count(*signals: bool | None) -> int:
    return sum(1 for s in signals if s is True)


def trade_group_key(politician_id: int, security_id: int | None, ticker: str | None, transaction_date: date, transaction_type: str) -> str:
    """A stable label for disclosures by the same politician in the same security, on the same date, of the same type. For display grouping only: rows are never
    merged, because differing owner codes (self, spouse, joint, dependent) can be separate reportable transactions."""
    return f"{politician_id}|{security_id if security_id is not None else (ticker or '')}|{transaction_date.isoformat()}|{transaction_type}"


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
    cfg: "ContextConfig" = field(default_factory=lambda: ContextConfig())

    @property
    def secondary(self) -> int:
        return secondary_count(self.size.anomaly, self.delay, self.excess)

    @property
    def meets_rule(self) -> bool:
        return meets_flag_rule(self.committee.value, self.size.anomaly, self.delay, self.excess, self.cfg.min_secondary_signals)

    @property
    def flagged(self) -> bool:
        return is_flagged(self.committee.value, self.size.anomaly, self.delay, self.excess, self.cfg.min_secondary_signals,
                          self.committee.temporal_status, self.cfg.require_temporal_verification)

    @property
    def pending_temporal(self) -> bool:
        """The rule is met but the committee evidence is not temporally verified, so the trade is not flagged."""
        return self.meets_rule and not self.flagged

    @property
    def count(self) -> int:
        return signal_count(self.committee.value, self.size.anomaly, self.delay, self.excess)

    def digest(self, version: str) -> str:
        """Stable hash of everything stored for the trade, so an unchanged result is recognised on rerun."""
        leg = self.perf.transaction
        payload = {
            "v": version, "m": self.mapping_version, "c": [self.committee.value, self.committee.reason, self.committee.temporal_status, self.committee.contradicted],
            "flag": [self.meets_rule, self.flagged, self.secondary],
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


def _mapping_evidence(m: Match, kind: str, trade: TradeInput, temporal: str) -> EvidenceItem:
    where = m.committee_name + (f" / {m.subcommittee_name}" if m.subcommittee_name else "")
    label = {"reviewed_direct_mapping": "Direct", "reviewed_related_mapping": "Related (supporting context only)",
             "rejected_current_assignment": "Rejected: a current seat would match, but official House records show it was not held on the transaction date"}[kind]
    return EvidenceItem(
        "committee_relevance", kind, f"mapping:{m.mapping_id}",
        f"{label}: {where}, SIC {m.sic_range}. {m.rationale}" + ("" if temporal == CONTRADICTED else f" Seat timing: {temporal.replace('_', ' ')}."),
        m.committee_code, m.subcommittee_code, m.mapping_id, m.source_url,
        {"committee_name": m.committee_name, "subcommittee_name": m.subcommittee_name, "scope": m.scope, "sic_range": m.sic_range, "level": m.level,
         "review_status": m.review_status, "jurisdiction_basis": m.jurisdiction_basis, "mapping_version": m.mapping_version,
         "source_citation": m.source_citation, "security_sic_code": trade.sic_code, "security_industry": trade.industry, "temporal_status": temporal},
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
    committee = committee_signal(matcher, assignments, trade.sic_code, trade.industry, trade.transaction_date)
    date_ok = transaction_date_problem(trade.transaction_date, trade.disclosure_date, today) is None
    size = size_signal(trade.amount_min, trade.amount_max, prior_sizes_sorted, cfg, date_ok)
    days, delay = delay_signal(trade.transaction_date, trade.disclosure_date, today, cfg)
    perf = compute_performance(
        ticker=trade.ticker, transaction_type=trade.transaction_type, transaction_date=trade.transaction_date,
        disclosure_date=trade.disclosure_date, series=series, benchmark=benchmark, benchmark_ticker=cfg.benchmark, today=today, horizon_days=cfg.excess_horizon_days,
    )
    excess = excess_signal(perf, cfg)

    evidence = [_mapping_evidence(m, "reviewed_direct_mapping", trade, committee.evidence_status[m.mapping_id]) for m in committee.direct]
    evidence += [_mapping_evidence(m, "reviewed_related_mapping", trade, committee.evidence_status[m.mapping_id]) for m in committee.related]
    for m in committee.rejected:
        evidence.append(_mapping_evidence(m, "rejected_current_assignment", trade, CONTRADICTED))
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
                                     f"Disclosed {days} days after the transaction (the signal marks a delay of more than {cfg.delay_days} days; filing circumstances are not known).",
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
    return ContextResult(trade.id, committee, size, days, delay, perf, excess, evidence, matcher.version, cfg)
