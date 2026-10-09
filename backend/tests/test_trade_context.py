"""Deterministic trade context signals: committee relevance, trade size, disclosure delay, excess return, and the flag."""

import ast
import json
from collections import Counter
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from poltracker.analyze_trade_context import AnalysisError, TradeContextAnalyzer
from poltracker.committee_industry import Assignment, CommitteeIndustryMatcher, Mapping
from poltracker.config import get_settings
from poltracker.models import (
    CommitteeAssignment, CommitteeIndustryMapping, Politician, PriceBar, Security, Trade, TradeContext, TradeContextEvidence,
)
from poltracker.performance import PriceSeries, compute_performance
from poltracker.trade_context import (
    CONTRADICTED, CURRENT_ASSIGNMENT_ONLY, ENGINE_VERSION, TEMPORALLY_VERIFIED, UNAVAILABLE, ContextConfig, TradeInput, analyze_trade, committee_signal, delay_signal,
    excess_signal, is_flagged, meets_flag_rule, percentile_rank, committee_history_status, effective_seats, secondary_count, size_signal, trade_group_key, trade_size_value,
)

ROOT = Path(__file__).resolve().parents[2]
CFG = ContextConfig()
TODAY = date(2026, 10, 7)
SRC = "https://example.gov/source"


def M(i, committee="AS00", sub=None, start=3720, end=3729, level="direct", status="reviewed", version="v1", name=None):
    return Mapping(id=i, chamber="house", committee_code=committee, subcommittee_code=sub, committee_name=name or f"Committee {committee}",
                   subcommittee_name=f"Sub {sub}" if sub else None, sic_start=start, sic_end=end, industry_pattern=None, relevance_level=level,
                   rationale=f"why {i}", jurisdiction_text="text", source_citation="cite", source_url=SRC,
                   reviewed_at=datetime(2026, 10, 1) if status == "reviewed" else None, mapping_version=version, review_status=status,
                   jurisdiction_basis="rule_x_text")


SNAPSHOT = date(2026, 10, 1)  # the Clerk snapshot's publish date in these tests


def A(committee="AS00", sub=None, start=None, end=None, congress=119, through=SNAPSHOT, complete=True, precision="exact_date"):
    """A seat. With `start` it is a dated seat from the official resolutions; without, a bare Clerk-snapshot seat."""
    if start is None:
        return Assignment(committee, f"Committee {committee}", sub, f"Sub {sub}" if sub else None, "house", temporal_precision="current_snapshot", congress_number=119, verified_through=SNAPSHOT)
    return Assignment(committee, f"Committee {committee}", sub, f"Sub {sub}" if sub else None, "house", start, end, congress, precision, None if end else through, complete)


SEAT_START = date(2025, 1, 3)  # a seat with a recorded start date is temporally verifiable


def sig(rows, seats, sic="3721"):
    return committee_signal(CommitteeIndustryMatcher(rows, "v1"), seats, sic, None)


# --- committee relevance ------------------------------------------------------------------------------------------

def test_a_reviewed_direct_mapping_makes_committee_relevance_true_and_is_stored_as_evidence():
    r = sig([M(1)], [A()])
    assert r.value is True and r.reason == "direct_match" and [m.mapping_id for m in r.direct] == [1] and r.related == []


def test_reviewed_related_only_is_not_a_signal_but_is_kept_as_supporting_context():
    r = sig([M(1, level="related")], [A()])
    assert r.value is False and r.direct == [] and [m.mapping_id for m in r.related] == [1]


def test_needs_review_direct_is_ignored_and_counted_as_pending():
    r = sig([M(1, status="needs_review")], [A()])
    assert r.value is False and r.direct == [] and r.related == [] and r.pending_review == 1


def test_a_reviewed_none_row_means_not_industry_specific_so_false():
    none = replace(M(1), relevance_level="none", sic_start=None, sic_end=None)
    assert sig([none], [A()]).value is False


def test_missing_sic_and_missing_assignments_are_unknown():
    assert (sig([M(1)], [A()], sic=None).value, sig([M(1)], [A()], sic=None).reason) == (None, "no_sic")
    assert (sig([M(1)], [], "3721").value, sig([M(1)], [], "3721").reason) == (None, "no_committee_assignments")


def test_an_unmapped_committee_makes_the_answer_unknown_unless_a_direct_match_exists():
    seats = [A("AS00"), A("ZZ00")]
    assert sig([M(1, start=4000, end=4010)], seats).value is None  # nothing matched and ZZ00 has no mapping: cannot say "no"
    assert sig([M(1)], seats).value is True  # a reviewed-direct match stands regardless


def test_parent_and_subcommittee_overlap_is_one_signal_with_several_evidence_rows():
    rows = [M(1, sub="AS25"), M(2), M(3, level="related", sub="AS25")]
    r = sig(rows, [A("AS00"), A("AS00", "AS25")])
    assert r.value is True and sorted(m.mapping_id for m in r.direct) == [1, 2] and [m.mapping_id for m in r.related] == [3]
    t = TradeInput(1, 1, "X", "buy", date(2026, 1, 5), date(2026, 1, 20), 1001, 15000, "3721", "Aircraft")
    res = analyze_trade(t, matcher=CommitteeIndustryMatcher(rows, "v1"), assignments=[A("AS00"), A("AS00", "AS25")], prior_sizes_sorted=[], series=None, benchmark=None, cfg=CFG, today=TODAY)
    kinds = Counter(e.evidence_type for e in res.evidence if e.signal_type == "committee_relevance")
    assert kinds == {"reviewed_direct_mapping": 2, "reviewed_related_mapping": 1} and res.count == 1  # the signal counts once


# --- trade size ---------------------------------------------------------------------------------------------------

def test_the_representative_value_is_a_midpoint_a_lower_bound_or_an_exact_figure_never_invented():
    assert trade_size_value(1001, 15000) == (8000.5, "range_midpoint")
    assert trade_size_value(50_000_000, None) == (50_000_000.0, "open_ended_lower_bound")  # open-ended: the conservative lower bound
    assert trade_size_value(500, 500) == (500.0, "exact_figure")
    assert trade_size_value(None, None) == (None, None) and trade_size_value(None, 100) == (None, None) and trade_size_value(200, 100) == (None, None)


def test_percentile_is_the_mid_rank_so_ties_count_half():
    prior = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(10, prior) == 100 and percentile_rank(0, prior) == 0 and percentile_rank(2, prior) == 37.5
    assert percentile_rank(5, [5.0] * 10) == 50  # a history of identical trades never makes the next identical one unusual


def test_size_signal_needs_enough_history_and_uses_the_threshold_inclusively():
    ten = [float(i) for i in range(1, 11)]
    assert size_signal(1, 15000, ten[:9], CFG).anomaly is None  # 9 earlier trades: insufficient history
    assert size_signal(1, 15000, ten[:9], CFG).sample_size == 9
    top = size_signal(100_000, 100_000, ten, CFG)
    assert top.anomaly is True and top.percentile == 100 and top.sample_size == 10 and top.median == 5.5
    base = [1.0] * 9 + [100.0]  # value 100 ranks: less=9, equal=1 -> 95
    assert size_signal(100, 100, base, CFG).percentile == 95 and size_signal(100, 100, base, CFG).anomaly is True
    nine_of_ten = [float(i) for i in range(1, 19)] + [1000.0] * 2  # value 1000: less=18, equal=2 -> 95; a lower one:
    edge = [1.0] * 5 + [50.0] * 4 + [100.0]  # value 50: less=5, equal=4 -> 70
    assert size_signal(50, 50, edge, CFG).percentile == 70 and size_signal(50, 50, edge, CFG).anomaly is False
    exactly_90 = [1.0] * 9 + [100.0] * 0 + [3.0] * 0
    assert size_signal(2, 2, [1.0] * 9 + [3.0], CFG).percentile == 90 and size_signal(2, 2, [1.0] * 9 + [3.0], CFG).anomaly is True  # 90 is inclusive
    assert nine_of_ten and exactly_90


def test_size_signal_is_unknown_without_a_usable_range_or_a_trustworthy_date():
    assert size_signal(None, None, [1.0] * 20, CFG).anomaly is None
    assert size_signal(1001, 15000, [1.0] * 20, CFG, date_ok=False).anomaly is None


def test_open_ended_ranges_are_compared_at_their_lower_bound():
    r = size_signal(50_000_001, None, [8000.5] * 12, CFG)
    assert r.basis == "open_ended_lower_bound" and r.value == 50_000_001.0 and r.anomaly is True


# --- disclosure delay ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tx,disc,expected", [
    (date(2026, 1, 1), date(2026, 1, 11), (10, False)),  # normal
    (date(2026, 1, 1), date(2026, 1, 31), (30, False)),  # 30 days is no longer the reference: PTRs are generally due 45 days after the transaction
    (date(2026, 1, 1), date(2026, 2, 15), (45, False)),  # exactly 45 days is within the reference
    (date(2026, 1, 1), date(2026, 2, 16), (46, True)),  # more than 45 days
    (date(2026, 1, 1), None, (None, None)),  # missing disclosure date
    (date(2026, 1, 20), date(2026, 1, 10), (None, None)),  # negative delay: rejected, not repaired
    (date(2027, 1, 1), date(2027, 3, 1), (None, None)),  # a transaction date in the future
    (date(2026, 9, 1), date(2027, 1, 1), (None, None)),  # a disclosure date in the future
])
def test_disclosure_delay(tx, disc, expected):
    assert delay_signal(tx, disc, TODAY, CFG) == expected


def test_the_delay_threshold_is_configurable_and_the_raw_delay_is_always_kept():
    assert delay_signal(date(2026, 1, 1), date(2026, 1, 11), TODAY, ContextConfig(delay_days=9)) == (10, True)
    assert delay_signal(date(2026, 1, 1), date(2026, 1, 11), TODAY, ContextConfig(delay_days=10)) == (10, False)
    assert ContextConfig().delay_days == 45 and ContextConfig().excess_return == 0.20 and ContextConfig().excess_horizon_days == 90


def test_delay_evidence_never_calls_a_filing_late_or_improper():
    t = TradeInput(1, 1, "X", "buy", date(2026, 1, 5), date(2026, 4, 20), 1001, 15000, "3721", None)
    res = analyze_trade(t, matcher=CommitteeIndustryMatcher([M(1)], "v1"), assignments=[A(start=SEAT_START)], prior_sizes_sorted=[], series=None, benchmark=None, cfg=CFG, today=TODAY)
    text = " ".join(e.description for e in res.evidence if e.signal_type == "disclosure_delay_signal").lower()
    assert "105 days" in text and not any(w in text for w in ("late", "unlawful", "illegal", "improper", "violation"))


# --- performance --------------------------------------------------------------------------------------------------

def series(start: date, prices: list[float]) -> PriceSeries:
    return PriceSeries([(start + timedelta(days=i), p) for i, p in enumerate(prices)])


def perf(ttype="buy", sec=None, bench=None, tx=date(2026, 1, 5), horizon=90):
    return compute_performance(ticker="X", transaction_type=ttype, transaction_date=tx, disclosure_date=tx + timedelta(days=5), series=sec, benchmark=bench,
                               benchmark_ticker="SPY", today=TODAY, horizon_days=horizon)


def flat(start, n, from_, to):
    return series(start, [from_ + (to - from_) * i / (n - 1) for i in range(n)])


def test_a_large_positive_excess_return_over_the_horizon_is_a_signal():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 190), flat(date(2026, 1, 1), 200, 100, 102)
    p = perf(sec=sec, bench=bench)
    assert p.status == "ok" and excess_signal(p, CFG) is True and p.transaction.excess_return > 0.1


def test_a_large_negative_excess_return_also_counts_by_absolute_value():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 40), flat(date(2026, 1, 1), 200, 100, 101)
    assert excess_signal(perf(sec=sec, bench=bench), CFG) is True


def test_a_sub_threshold_excess_return_is_not_a_signal_and_the_threshold_is_inclusive():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 105), flat(date(2026, 1, 1), 200, 100, 100)
    p = perf(sec=sec, bench=bench)
    assert excess_signal(p, CFG) is False and excess_signal(p, ContextConfig(excess_return=p.transaction.excess_return)) is True


def test_missing_prices_or_an_unelapsed_horizon_are_unknown():
    assert excess_signal(perf(sec=None, bench=None), CFG) is None
    short = flat(date(2026, 1, 1), 40, 100, 150)  # prices stop 40 days after the start: a 90-day window has not elapsed
    p = perf(sec=short, bench=short)
    assert p.status == "horizon_not_elapsed" and excess_signal(p, CFG) is None


def test_a_sell_keeps_the_raw_security_figure_and_stores_the_direction_adjusted_one_separately():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 190), flat(date(2026, 1, 1), 200, 100, 100)
    p = perf("sell", sec, bench)
    raw = p.transaction.excess_return
    assert raw > 0 and p.direction_adjusted["transaction_excess_return"] == -raw and excess_signal(p, CFG) is True  # the signal reads the raw figure


def test_an_invalid_transaction_date_gives_no_excess_signal():
    sec = flat(date(2026, 1, 1), 300, 100, 150)
    p = compute_performance(ticker="X", transaction_type="buy", transaction_date=date(2027, 1, 1), disclosure_date=date(2027, 2, 1), series=sec, benchmark=sec,
                            benchmark_ticker="SPY", today=TODAY, horizon_days=90)
    assert p.status == "invalid_date" and excess_signal(p, CFG) is None


def test_the_default_performance_behaviour_without_a_horizon_is_unchanged():
    sec, bench = flat(date(2026, 1, 1), 100, 100, 150), flat(date(2026, 1, 1), 100, 100, 100)
    p = perf(sec=sec, bench=bench, horizon=None)
    assert p.status == "ok" and p.latest_date == date(2026, 4, 10) and p.transaction.return_ == pytest.approx(150 / (100 + 50 * 4 / 99) - 1)


# --- the flag -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("committee,size,delay,excess,flagged", [
    (True, True, True, False, True),  # committee + size + delay
    (True, True, False, True, True),  # committee + size + excess
    (True, False, True, True, True),  # committee + delay + excess
    (True, True, True, True, True),  # committee + all three
    (True, True, False, False, False),  # committee + one secondary: context shown, not flagged
    (True, False, True, False, False),
    (True, False, False, True, False),
    (True, False, False, False, False),
    (True, True, None, None, False),  # unknown never counts as true
    (False, True, True, True, False),  # three secondary signals without committee relevance
    (None, True, True, True, False),
    (False, False, False, True, False),  # performance alone never flags
    (False, True, False, False, False),
])
def test_the_default_rule_needs_committee_relevance_and_two_secondary_signals(committee, size, delay, excess, flagged):
    assert is_flagged(committee, size, delay, excess) is flagged and meets_flag_rule(committee, size, delay, excess) is flagged
    assert secondary_count(size, delay, excess) == sum(1 for x in (size, delay, excess) if x is True)


def test_the_minimum_number_of_secondary_signals_is_configurable():
    assert is_flagged(True, True, False, False, min_secondary=1) and not is_flagged(True, True, False, False, min_secondary=2)
    assert not is_flagged(False, True, True, True, min_secondary=1)  # committee relevance stays mandatory under any setting


def test_a_related_or_needs_review_mapping_plus_two_secondary_signals_does_not_flag():
    prior = [8000.5] * 12
    for row in (M(1, level="related"), M(1, status="needs_review")):
        t = TradeInput(1, 1, "X", "buy", date(2026, 1, 1), date(2026, 3, 1), 250001, 500000, "3721", None)  # size anomaly and a 59-day delay: two true secondaries
        res = analyze_trade(t, matcher=CommitteeIndustryMatcher([row], "v1"), assignments=[A(start=SEAT_START)], prior_sizes_sorted=prior, series=None, benchmark=None, cfg=CFG, today=TODAY)
        assert res.secondary == 2 and res.committee.value is False and res.flagged is False and res.meets_rule is False
    ok = analyze_trade(t, matcher=CommitteeIndustryMatcher([M(1)], "v1"), assignments=[A(start=SEAT_START)], prior_sizes_sorted=prior, series=None, benchmark=None, cfg=CFG, today=TODAY)
    assert ok.flagged is True and ok.count == 3 and ok.secondary == 2


# --- temporal status of committee evidence ------------------------------------------------------------------------

def test_committee_history_status_verifies_contradicts_or_stays_unknown():
    tx = date(2026, 3, 1)
    open_seat = [A(start=date(2025, 1, 14))]
    assert committee_history_status(open_seat, tx) == "verified"
    assert committee_history_status([A(start=date(2025, 1, 14), end=date(2026, 6, 1))], tx) == "verified"
    assert committee_history_status([A()], tx) == "unknown"  # a bare snapshot seat says nothing about that day
    assert committee_history_status([A(start=date(2026, 5, 1))], tx) == "contradicted"  # not yet elected
    assert committee_history_status([A(start=date(2025, 1, 14), end=date(2026, 2, 1))], tx) == "contradicted"  # removed before the trade
    assert committee_history_status([A(start=date(2025, 1, 14), end=date(2025, 6, 1)), A(start=date(2026, 5, 1))], tx) == "contradicted"  # between two stints
    assert committee_history_status([A(start=date(2026, 5, 1), complete=False)], tx) == "unknown"  # an incomplete scan never proves absence
    assert committee_history_status([A(start=date(2025, 1, 14), through=date(2026, 1, 1))], tx) == "unknown"  # open seat, confirmed only up to Jan 1: unknown, not absent
    assert committee_history_status([A(start=date(2025, 1, 14), congress=118)], tx) == "unknown"  # another Congress's record says nothing about this one


def test_a_congress_precision_seat_verifies_only_within_that_congress_and_yields_to_a_complete_exact_record():
    seat = Assignment("AS00", "Committee AS00", None, None, "house", None, None, 119, "congress")
    assert committee_history_status([seat], date(2026, 3, 1)) == "verified" and committee_history_status([seat], date(2024, 3, 1)) == "unknown"
    assert committee_history_status([seat, A(start=date(2026, 5, 1))], date(2026, 3, 1)) == "contradicted"  # contradictory exact information wins


def test_effective_seats_drops_contradicted_committees_and_their_subcommittee_seats_and_never_promotes_a_subcommittee():
    tx = date(2026, 3, 1)
    gone = [A("AS00", start=date(2026, 5, 1)), A("AS00"), A("AS00", "AS25")]
    assert effective_seats(gone, tx) == []  # the committee seat began later, so neither the snapshot seat nor the subcommittee seat applied
    held = [A("AS00", start=date(2025, 1, 14)), A("AS00"), A("AS00", "AS25")]
    got = {(a.committee_code, a.subcommittee_code): st for a, st in effective_seats(held, tx)}
    assert got[("AS00", None)] == TEMPORALLY_VERIFIED and got[("AS00", "AS25")] == CURRENT_ASSIGNMENT_ONLY  # no dated record of the subcommittee seat


def test_a_current_snapshot_seat_gives_a_match_but_only_current_assignment_status():
    r = committee_signal(CommitteeIndustryMatcher([M(1)], "v1"), [A()], "3721", None, date(2026, 3, 1))
    assert r.value is True and r.temporal_status == CURRENT_ASSIGNMENT_ONLY and r.evidence_status == {1: CURRENT_ASSIGNMENT_ONLY}
    v = committee_signal(CommitteeIndustryMatcher([M(1)], "v1"), [A(start=SEAT_START)], "3721", None, date(2026, 3, 1))
    assert v.value is True and v.temporal_status == TEMPORALLY_VERIFIED


def test_a_current_seat_the_dated_record_rejects_is_contradicted_and_kept_only_as_rejected_evidence():
    seats = [A(start=date(2026, 5, 1)), A()]  # elected in May 2026; the snapshot also lists the seat
    r = committee_signal(CommitteeIndustryMatcher([M(1)], "v1"), seats, "3721", None, date(2026, 3, 1))
    assert r.value is False and r.contradicted and r.temporal_status == CONTRADICTED and r.direct == [] and [m.mapping_id for m in r.rejected] == [1]
    assert r.reason == "seat_not_held_on_transaction_date"
    t = TradeInput(1, 1, "X", "buy", date(2026, 3, 1), date(2026, 6, 1), 250001, 500000, "3721", None)
    res = analyze_trade(t, matcher=CommitteeIndustryMatcher([M(1)], "v1"), assignments=seats, prior_sizes_sorted=[8000.5] * 12, series=None, benchmark=None, cfg=CFG, today=TODAY)
    assert res.secondary == 2 and not res.meets_rule and not res.flagged  # two secondaries, but the seat was not held
    assert [e.evidence_type for e in res.evidence if e.signal_type == "committee_relevance"] == ["rejected_current_assignment"]


def test_a_verified_committee_seat_verifies_a_committee_mapping_but_not_a_subcommittee_only_match():
    seats = [A("AS00", start=date(2025, 1, 14)), A("AS00"), A("AS00", "AS25")]
    committee_level = committee_signal(CommitteeIndustryMatcher([M(1)], "v1"), seats, "3721", None, date(2026, 3, 1))
    assert committee_level.value is True and committee_level.temporal_status == TEMPORALLY_VERIFIED
    sub_only = committee_signal(CommitteeIndustryMatcher([M(2, sub="AS25")], "v1"), seats, "3721", None, date(2026, 3, 1))
    assert sub_only.value is True and sub_only.temporal_status == CURRENT_ASSIGNMENT_ONLY and sub_only.evidence_status == {2: CURRENT_ASSIGNMENT_ONLY}
    both = committee_signal(CommitteeIndustryMatcher([M(1), M(2, sub="AS25")], "v1"), seats, "3721", None, date(2026, 3, 1))
    assert both.temporal_status == TEMPORALLY_VERIFIED and both.evidence_status == {1: TEMPORALLY_VERIFIED, 2: CURRENT_ASSIGNMENT_ONLY}  # the sub match stays unverified


def test_no_committee_data_is_unavailable():
    r = committee_signal(CommitteeIndustryMatcher([M(1)], "v1"), [], "3721", None, date(2026, 3, 1))
    assert r.value is None and r.temporal_status == UNAVAILABLE


def test_current_assignment_only_evidence_never_flags_but_is_marked_as_pending_verification():
    prior = [8000.5] * 12
    t = TradeInput(1, 1, "X", "buy", date(2026, 1, 1), date(2026, 3, 1), 250001, 500000, "3721", None)

    def go(seat, cfg=CFG):
        return analyze_trade(t, matcher=CommitteeIndustryMatcher([M(1)], "v1"), assignments=[seat], prior_sizes_sorted=prior, series=None, benchmark=None, cfg=cfg, today=TODAY)

    current = go(A())
    assert current.committee.value is True and current.meets_rule and not current.flagged and current.pending_temporal  # the relationship is kept as context
    assert go(A(start=SEAT_START)).flagged and not go(A(start=SEAT_START)).pending_temporal
    assert go(A(), ContextConfig(require_temporal_verification=False)).flagged  # a what-if comparison only


# --- grouping --------------------------------------------------------------------------------------------------------

def test_the_group_key_is_stable_and_depends_only_on_politician_security_date_and_type():
    a = trade_group_key(1, 5, "BA", date(2026, 1, 5), "buy")
    assert a == trade_group_key(1, 5, "BA", date(2026, 1, 5), "buy") and a != trade_group_key(1, 5, "BA", date(2026, 1, 5), "sell")
    assert a != trade_group_key(2, 5, "BA", date(2026, 1, 5), "buy") and a != trade_group_key(1, 5, "BA", date(2026, 1, 6), "buy")
    assert trade_group_key(1, None, "ZZ", date(2026, 1, 5), "buy").startswith("1|ZZ|")


# --- storage and the analyzer --------------------------------------------------------------------------------------

def seed(factory, n_prior=12, mapping_status="reviewed", with_prices=False, dated_seat=False):
    """One politician on AS00 with n_prior earlier trades of $1,001-$15,000 and one large aircraft trade (SIC 3721)."""
    with factory() as s:
        pol = Politician(canonical_key="a-b", name="A B", chamber="house")
        other = Politician(canonical_key="c-d", name="C D", chamber="house")
        sec = Security(ticker="BA", sic_code="3721", industry="Aircraft")
        plain = Security(ticker="KO", sic_code="2086", industry="Bottled & Canned Soft Drinks")
        s.add_all([pol, other, sec, plain])
        s.flush()
        s.add(CommitteeAssignment(politician_id=pol.id, committee_name="Committee on Armed Services", committee_code="AS00", subcommittee_code="", chamber="house", source="t",
                                 start_date=SEAT_START if dated_seat else None,
                                 congress_number=119, temporal_precision="exact_date" if dated_seat else "current_snapshot", verified_through=SNAPSHOT,
                                 history_complete=True if dated_seat else None))
        s.add(CommitteeIndustryMapping(chamber="house", committee_code="AS00", committee_name="Armed Services", sic_start=3720, sic_end=3729, relevance_level="direct",
                                       rationale="aircraft", source_url=SRC, mapping_version="v1", review_status=mapping_status,
                                       reviewed_at=datetime(2026, 10, 1) if mapping_status == "reviewed" else None, jurisdiction_basis="rule_x_text"))
        s.add(CommitteeIndustryMapping(chamber="house", committee_code="AS00", committee_name="Armed Services", sic_start=2000, sic_end=2099, relevance_level="related",
                                       rationale="food", source_url=SRC, mapping_version="v1", review_status="reviewed", reviewed_at=datetime(2026, 10, 1), jurisdiction_basis="rule_x_text"))

        def trade(p, security, ttype, tx, disc, lo, hi, fp):
            t = Trade(source="t", fingerprint=fp, politician_id=p.id, security_id=security.id, politician_name=p.name, chamber="house", ticker=security.ticker,
                      transaction_type=ttype, transaction_date=tx, disclosure_date=disc, amount_min=lo, amount_max=hi)
            s.add(t)
            return t

        for i in range(n_prior):
            trade(pol, plain, "buy", date(2026, 1, 1) + timedelta(days=i), date(2026, 1, 10) + timedelta(days=i), 1001, 15000, f"p{i}")
        big = trade(pol, sec, "buy", date(2026, 2, 20), date(2026, 4, 20), 250001, 500000, "big")  # a 59-day delay, much larger than the history
        trade(other, sec, "buy", date(2026, 3, 1), date(2026, 3, 5), 1000001, 5000000, "other")  # another politician: must not affect A B's percentile
        s.flush()
        ids = {"pol": pol.id, "big": big.id, "other_pol": other.id}
        if with_prices:
            for security, start, end in ((sec, 100, 140), (plain, 50, 50)):
                for i in range(400):
                    s.add(PriceBar(security_id=security.id, date=date(2025, 12, 1) + timedelta(days=i), adj_close=start + (end - start) * i / 399, close=start, provider="t"))
            spy = Security(ticker="SPY")
            s.add(spy)
            s.flush()
            for i in range(400):
                s.add(PriceBar(security_id=spy.id, date=date(2025, 12, 1) + timedelta(days=i), adj_close=100 + 2 * i / 399, close=100, provider="t"))
        s.commit()
    return ids


def run(factory, **kw):
    return TradeContextAnalyzer(factory, ContextConfig(), today=TODAY).run(**kw)


def test_the_analyzer_flags_a_trade_with_verified_committee_evidence_and_two_secondary_signals(session_factory):
    ids = seed(session_factory, dated_seat=True)
    summary = run(session_factory)
    assert summary.evaluated == 12 + 2 and summary.flagged == 1 and summary.committee[True] == 1 and summary.committee[None] == 1  # the other politician has no seats
    assert summary.meets_rule == 1 and summary.pending_temporal == 0 and summary.secondary_distribution[2] == 1
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert (c.committee_relevance, c.trade_size_anomaly, c.disclosure_delay_signal, c.flagged_for_contextual_review, c.signal_count) == (True, True, True, True, 3)
        assert (c.secondary_signal_count, c.committee_temporal_status, c.meets_flag_rule) == (2, "temporally_verified", True)
        assert c.trade_size_sample_size == 12 and c.trade_size_percentile == 100 and c.disclosure_delay_days == 59 and c.trade_size_basis == "range_midpoint"
        assert c.context_version == ENGINE_VERSION and c.mapping_version == "v1"
        direct = [e for e in c.evidence if e.evidence_type == "reviewed_direct_mapping"]
        assert len(direct) == 1 and direct[0].committee_code == "AS00" and direct[0].source_url == SRC
        meta = json.loads(direct[0].metadata_json)
        assert meta["review_status"] == "reviewed" and meta["temporal_status"] == "temporally_verified"


def test_with_snapshot_only_seats_the_committee_match_is_kept_but_nothing_is_flagged(session_factory):
    ids = seed(session_factory)  # the seat has no recorded start date, like every House Clerk seat today
    summary = run(session_factory)
    assert summary.committee[True] == 1 and summary.meets_rule == 1 and summary.flagged == 0 and summary.pending_temporal == 1
    assert summary.temporal_status_committee == {"current_assignment_only": 1}
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert c.committee_relevance is True and c.committee_temporal_status == "current_assignment_only" and c.meets_flag_rule is True and c.flagged_for_contextual_review is False


def test_size_is_compared_only_with_the_same_politicians_earlier_trades(session_factory):
    ids = seed(session_factory)
    run(session_factory)
    with session_factory() as s:
        other = s.scalar(select(TradeContext).join(Trade, Trade.id == TradeContext.trade_id).where(Trade.politician_id == ids["other_pol"]))
        assert other.trade_size_sample_size == 0 and other.trade_size_anomaly is None  # no earlier trades of its own, however large the first trade is
        big = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert big.trade_size_sample_size == 12  # the other politician's $1M+ trade is not in the history


def test_early_trades_have_unknown_size_because_they_lack_history(session_factory):
    seed(session_factory)
    run(session_factory)
    with session_factory() as s:
        n = s.scalar(select(func.count()).select_from(TradeContext).where(TradeContext.trade_size_anomaly.is_(None)))
        assert n == 10 + 1  # earlier trades with 0..9 trades of history, plus the other politician's lone trade
        pct = s.scalars(select(TradeContext.trade_size_sample_size).join(Trade, Trade.id == TradeContext.trade_id).where(Trade.fingerprint.like("p%")).order_by(Trade.transaction_date)).all()
        assert pct == list(range(12))  # a trade only ever sees strictly earlier days


def test_a_needs_review_mapping_never_creates_the_signal_or_a_flag(session_factory):
    seed(session_factory, mapping_status="needs_review")
    summary = run(session_factory)
    assert summary.committee[True] == 0 and summary.flagged == 0 and summary.needs_review_matches_ignored == 1


def test_rerunning_is_idempotent_and_changes_no_ids(session_factory):
    ids = seed(session_factory)
    first = run(session_factory)
    with session_factory() as s:
        before = (s.scalar(select(func.count()).select_from(TradeContext)), s.scalar(select(func.count()).select_from(TradeContextEvidence)),
                  [(t.id, t.politician_id, t.security_id) for t in s.scalars(select(Trade).order_by(Trade.id))], s.scalar(select(func.max(TradeContext.analyzed_at))),
                  s.scalar(select(func.count()).select_from(Security)), s.scalar(select(func.count()).select_from(Politician)))
    second = run(session_factory)
    assert (first.inserted, first.unchanged) == (14, 0) and (second.inserted, second.updated, second.unchanged) == (0, 0, 14)
    with session_factory() as s:
        after = (s.scalar(select(func.count()).select_from(TradeContext)), s.scalar(select(func.count()).select_from(TradeContextEvidence)),
                 [(t.id, t.politician_id, t.security_id) for t in s.scalars(select(Trade).order_by(Trade.id))], s.scalar(select(func.max(TradeContext.analyzed_at))),
                 s.scalar(select(func.count()).select_from(Security)), s.scalar(select(func.count()).select_from(Politician)))
    assert before == after and ids["big"]


def test_dry_run_writes_nothing_but_reports_the_same_counts(session_factory):
    seed(session_factory)
    dry = run(session_factory, dry_run=True)
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TradeContext)) == 0 and s.scalar(select(func.count()).select_from(TradeContextEvidence)) == 0
    real = run(session_factory)
    assert (dry.flagged, dry.committee, dry.inserted) == (real.flagged, real.committee, real.inserted) and dry.dry_run and "DRY RUN" in dry.to_text()


def test_a_changed_input_updates_the_row_in_place_and_force_rewrites_it(session_factory):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    with session_factory() as s:
        s.get(Trade, ids["big"]).disclosure_date = date(2026, 2, 21)  # a 1-day delay now
        s.commit()
    changed = run(session_factory)
    assert (changed.updated, changed.unchanged) == (1, 13)
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert c.disclosure_delay_signal is False and c.trade_size_anomaly is True and c.flagged_for_contextual_review is False  # one secondary signal is not enough
        assert s.scalar(select(func.count()).select_from(TradeContext).where(TradeContext.trade_id == ids["big"])) == 1
    assert run(session_factory, force=True).updated == 14


def test_a_custom_threshold_gets_its_own_version_and_never_overwrites_the_default_rows(session_factory):
    seed(session_factory)
    run(session_factory)
    custom = TradeContextAnalyzer(session_factory, ContextConfig(delay_days=60), today=TODAY).run()
    assert custom.context_version != ENGINE_VERSION and custom.inserted == 14
    with session_factory() as s:
        versions = Counter(s.scalars(select(TradeContext.context_version)))
        assert versions[ENGINE_VERSION] == 14 and versions[custom.context_version] == 14


def test_a_new_mapping_version_adds_rows_and_keeps_the_old_ones(session_factory):
    seed(session_factory)
    run(session_factory)
    with session_factory() as s:
        for m in list(s.scalars(select(CommitteeIndustryMapping))):
            s.add(CommitteeIndustryMapping(chamber=m.chamber, committee_code=m.committee_code, committee_name=m.committee_name, sic_start=m.sic_start, sic_end=m.sic_end,
                                           relevance_level=m.relevance_level, rationale=m.rationale, source_url=m.source_url, mapping_version="v2",
                                           review_status="needs_review", jurisdiction_basis=m.jurisdiction_basis))
        s.commit()
    v2 = TradeContextAnalyzer(session_factory, ContextConfig(), today=TODAY, mapping_version="v2").run()
    assert v2.mapping_version == "v2" and v2.inserted == 14 and v2.committee[True] == 0
    with session_factory() as s:
        assert Counter(s.scalars(select(TradeContext.mapping_version))) == {"v1": 14, "v2": 14}


def test_selectors_limit_the_trades_analyzed(session_factory):
    ids = seed(session_factory)
    assert run(session_factory, dry_run=True, trade_ids=[ids["big"]]).evaluated == 1
    assert run(session_factory, dry_run=True, ticker="ba").evaluated == 2
    assert run(session_factory, dry_run=True, politician="C D").evaluated == 1 and run(session_factory, dry_run=True, politician=str(ids["pol"])).evaluated == 13
    assert run(session_factory, dry_run=True, limit=3).evaluated == 3


def test_excess_return_is_computed_from_cached_prices_and_stored_with_its_horizon(session_factory):
    ids = seed(session_factory, with_prices=True)
    run(session_factory)
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert c.performance_status == "ok" and c.excess_return == pytest.approx(c.security_return - c.spy_return) and c.performance_horizon_days == 90
        assert c.performance_through_date == c.performance_anchor_date + timedelta(days=90) and c.excess_return_direction_adjusted == pytest.approx(c.excess_return)


def test_no_mappings_loaded_is_a_clear_error(session_factory):
    with pytest.raises(AnalysisError):
        run(session_factory)


def test_evidence_is_unique_per_context_signal_and_key(session_factory):
    seed(session_factory)
    run(session_factory)
    with session_factory() as s:
        e = s.scalars(select(TradeContextEvidence)).first()
        s.add(TradeContextEvidence(trade_context_id=e.trade_context_id, trade_id=e.trade_id, signal_type=e.signal_type, evidence_type=e.evidence_type, evidence_key=e.evidence_key, description="dup"))
        with pytest.raises(IntegrityError):
            s.flush()
        s.rollback()


# --- no network, no AI --------------------------------------------------------------------------------------------

def test_the_analysis_makes_no_network_connection(session_factory, monkeypatch):
    import socket

    seed(session_factory)

    def blocked(*a, **k):
        raise AssertionError("the context engine must not touch the network")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    assert run(session_factory).evaluated == 14


def test_the_context_modules_import_no_network_or_ai_library():
    banned = {"httpx", "requests", "urllib", "urllib3", "socket", "openai", "anthropic", "aiohttp", "yfinance", "poltracker.providers", "poltracker.politician_llm"}
    for name in ("trade_context.py", "analyze_trade_context.py"):
        tree = ast.parse((ROOT / "backend" / "poltracker" / name).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names} | {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mod = ("." * node.level) + (node.module or "")
                imported |= {mod.lstrip(".").split(".")[0], "poltracker." + mod.lstrip(".")} if node.level else {(node.module or "").split(".")[0], node.module or ""}
        assert not imported & banned, (name, imported & banned)


# --- migration ----------------------------------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm12.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def test_migration_0012_adds_only_the_two_tables_and_leaves_existing_data_untouched(db):
    engine, cfg = db
    command.upgrade(cfg, "0011")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (1, 'a', 'A', 'house', '2026-01-01')")
    before = set(sa.inspect(engine).get_table_names())
    command.upgrade(cfg, "head")
    assert set(sa.inspect(engine).get_table_names()) - before == {"trade_context", "trade_context_evidence", "trade_context_analysis"}
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 1 and c.exec_driver_sql("select version_num from alembic_version").scalar() == "0015"
    command.downgrade(cfg, "0011")
    assert not {"trade_context", "trade_context_evidence"} & set(sa.inspect(engine).get_table_names())
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 1
    command.upgrade(cfg, "head")


def test_the_models_match_the_migrated_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name


def test_migration_0013_adds_only_three_nullable_columns_and_keeps_existing_rows(db):
    engine, cfg = db
    command.upgrade(cfg, "0012")
    new = {"secondary_signal_count", "committee_temporal_status", "meets_flag_rule"}
    assert not new & {c["name"] for c in sa.inspect(engine).get_columns("trade_context")}
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (1, 'a', 'A', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into trades (id, source, fingerprint, politician_id, politician_name, chamber, transaction_type, transaction_date, created_at) "
                          "values (1, 's', 'f', 1, 'A', 'house', 'buy', '2026-01-01', '2026-01-01')")
        c.exec_driver_sql("insert into trade_context (id, trade_id, context_version, mapping_version, result_digest, analyzed_at, signal_count, flagged_for_contextual_review) "
                          "values (1, 1, '2026.1', 'm', 'd', '2026-01-02', 1, 0)")
    command.upgrade(cfg, "head")
    cols = {c["name"]: c for c in sa.inspect(engine).get_columns("trade_context")}
    assert new <= set(cols) and all(cols[n]["nullable"] for n in new)
    with engine.connect() as c:
        assert tuple(c.exec_driver_sql("select context_version, signal_count, secondary_signal_count, committee_temporal_status from trade_context").one()) == ("2026.1", 1, None, None)
    command.downgrade(cfg, "0012")
    assert not new & {c["name"] for c in sa.inspect(engine).get_columns("trade_context")}
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from trade_context").scalar() == 1
    command.upgrade(cfg, "head")
