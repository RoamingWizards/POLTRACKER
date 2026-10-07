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
    ENGINE_VERSION, ContextConfig, TradeInput, analyze_trade, committee_signal, delay_signal, excess_signal, is_flagged, percentile_rank,
    size_signal, trade_size_value,
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


def A(committee="AS00", sub=None):
    return Assignment(committee, f"Committee {committee}", sub, f"Sub {sub}" if sub else None)


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
    (date(2026, 1, 1), date(2026, 1, 31), (30, True)),  # exactly the threshold
    (date(2026, 1, 1), date(2026, 1, 30), (29, False)),
    (date(2026, 1, 1), None, (None, None)),  # missing disclosure date
    (date(2026, 1, 20), date(2026, 1, 10), (None, None)),  # negative delay: rejected, not repaired
    (date(2027, 1, 1), date(2027, 3, 1), (None, None)),  # a transaction date in the future
    (date(2026, 9, 1), date(2027, 1, 1), (None, None)),  # a disclosure date in the future
])
def test_disclosure_delay(tx, disc, expected):
    assert delay_signal(tx, disc, TODAY, CFG) == expected


def test_the_delay_threshold_is_configurable():
    assert delay_signal(date(2026, 1, 1), date(2026, 1, 11), TODAY, ContextConfig(delay_days=10)) == (10, True)


# --- performance --------------------------------------------------------------------------------------------------

def series(start: date, prices: list[float]) -> PriceSeries:
    return PriceSeries([(start + timedelta(days=i), p) for i, p in enumerate(prices)])


def perf(ttype="buy", sec=None, bench=None, tx=date(2026, 1, 5), horizon=90):
    return compute_performance(ticker="X", transaction_type=ttype, transaction_date=tx, disclosure_date=tx + timedelta(days=5), series=sec, benchmark=bench,
                               benchmark_ticker="SPY", today=TODAY, horizon_days=horizon)


def flat(start, n, from_, to):
    return series(start, [from_ + (to - from_) * i / (n - 1) for i in range(n)])


def test_a_large_positive_excess_return_over_the_horizon_is_a_signal():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 130), flat(date(2026, 1, 1), 200, 100, 102)
    p = perf(sec=sec, bench=bench)
    assert p.status == "ok" and excess_signal(p, CFG) is True and p.transaction.excess_return > 0.1


def test_a_large_negative_excess_return_also_counts_by_absolute_value():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 70), flat(date(2026, 1, 1), 200, 100, 101)
    assert excess_signal(perf(sec=sec, bench=bench), CFG) is True


def test_a_small_excess_return_is_not_a_signal_and_the_threshold_is_inclusive():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 105), flat(date(2026, 1, 1), 200, 100, 100)
    p = perf(sec=sec, bench=bench)
    assert excess_signal(p, CFG) is False and excess_signal(p, ContextConfig(excess_return=p.transaction.excess_return)) is True


def test_missing_prices_or_an_unelapsed_horizon_are_unknown():
    assert excess_signal(perf(sec=None, bench=None), CFG) is None
    short = flat(date(2026, 1, 1), 40, 100, 150)  # prices stop 40 days after the start: a 90-day window has not elapsed
    p = perf(sec=short, bench=short)
    assert p.status == "horizon_not_elapsed" and excess_signal(p, CFG) is None


def test_a_sell_keeps_the_raw_security_figure_and_stores_the_direction_adjusted_one_separately():
    sec, bench = flat(date(2026, 1, 1), 200, 100, 130), flat(date(2026, 1, 1), 200, 100, 100)
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
    (True, True, False, False, True),  # committee + unusual size
    (True, False, True, False, True),  # committee + long delay
    (True, False, False, True, True),  # committee + excess return
    (True, False, False, False, False),  # committee relevance alone: context shown, not flagged
    (True, None, None, None, False),
    (False, False, False, True, False),  # excess return alone never flags
    (False, True, False, False, False),  # a large trade alone never flags
    (False, True, False, True, False),  # size + excess without committee relevance
    (None, True, True, True, False),  # unknown committee relevance never counts
    (False, True, True, True, False),
])
def test_the_flag_requires_committee_relevance_and_one_secondary_signal(committee, size, delay, excess, flagged):
    assert is_flagged(committee, size, delay, excess) is flagged


def test_a_related_or_needs_review_mapping_plus_a_secondary_signal_does_not_flag():
    for row in (M(1, level="related"), M(1, status="needs_review")):
        t = TradeInput(1, 1, "X", "buy", date(2026, 1, 1), date(2026, 3, 1), 1001, 15000, "3721", None)  # a 59-day delay: a true secondary signal
        res = analyze_trade(t, matcher=CommitteeIndustryMatcher([row], "v1"), assignments=[A()], prior_sizes_sorted=[], series=None, benchmark=None, cfg=CFG, today=TODAY)
        assert res.delay is True and res.committee.value is False and res.flagged is False
    ok = analyze_trade(t, matcher=CommitteeIndustryMatcher([M(1)], "v1"), assignments=[A()], prior_sizes_sorted=[], series=None, benchmark=None, cfg=CFG, today=TODAY)
    assert ok.flagged is True and ok.count == 2


# --- storage and the analyzer --------------------------------------------------------------------------------------

def seed(factory, n_prior=12, mapping_status="reviewed", with_prices=False):
    """One politician on AS00 with n_prior earlier trades of $1,001-$15,000 and one large aircraft trade (SIC 3721)."""
    with factory() as s:
        pol = Politician(canonical_key="a-b", name="A B", chamber="house")
        other = Politician(canonical_key="c-d", name="C D", chamber="house")
        sec = Security(ticker="BA", sic_code="3721", industry="Aircraft")
        plain = Security(ticker="KO", sic_code="2086", industry="Bottled & Canned Soft Drinks")
        s.add_all([pol, other, sec, plain])
        s.flush()
        s.add(CommitteeAssignment(politician_id=pol.id, committee_name="Committee on Armed Services", committee_code="AS00", subcommittee_code="", chamber="house", source="t"))
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
        big = trade(pol, sec, "buy", date(2026, 2, 20), date(2026, 3, 30), 250001, 500000, "big")  # a 38-day delay, much larger than the history
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


def test_the_analyzer_flags_a_reviewed_direct_committee_trade_with_a_large_size_and_long_delay(session_factory):
    ids = seed(session_factory)
    summary = run(session_factory)
    assert summary.evaluated == 12 + 2 and summary.flagged == 1 and summary.committee[True] == 1 and summary.committee[None] == 1  # the other politician has no committee seats
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert (c.committee_relevance, c.trade_size_anomaly, c.disclosure_delay_signal, c.flagged_for_contextual_review, c.signal_count) == (True, True, True, True, 3)
        assert c.trade_size_sample_size == 12 and c.trade_size_percentile == 100 and c.disclosure_delay_days == 38 and c.trade_size_basis == "range_midpoint"
        assert c.context_version == ENGINE_VERSION and c.mapping_version == "v1"
        direct = [e for e in c.evidence if e.evidence_type == "reviewed_direct_mapping"]
        assert len(direct) == 1 and direct[0].committee_code == "AS00" and direct[0].source_url == SRC and json.loads(direct[0].metadata_json)["review_status"] == "reviewed"


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
    ids = seed(session_factory)
    run(session_factory)
    with session_factory() as s:
        s.get(Trade, ids["big"]).disclosure_date = date(2026, 2, 21)  # a 1-day delay now
        s.commit()
    changed = run(session_factory)
    assert (changed.updated, changed.unchanged) == (1, 13)
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == ids["big"]))
        assert c.disclosure_delay_signal is False and c.flagged_for_contextual_review is True  # size still qualifies
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
    assert set(sa.inspect(engine).get_table_names()) - before == {"trade_context", "trade_context_evidence"}
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 1 and c.exec_driver_sql("select version_num from alembic_version").scalar() == "0012"
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
