"""Committee/industry relevance: deterministic, explainable, no AI, no network. Plus the shipped mapping file."""

import ast
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from poltracker.committee_industry import (
    Assignment, CommitteeIndustryMatcher, Mapping, MappingError, load_assignments, load_mappings, load_rows, parse_sic, sync_mappings, validate_rows,
)
from poltracker.committee_industry_report import evaluate_trades
from poltracker.models import CommitteeAssignment, CommitteeIndustryMapping, Politician, Security, Trade

ROOT = Path(__file__).resolve().parents[2]
SRC = "https://example.gov/rule-x"


def M(i, committee="AS00", sub=None, start=3720, end=3729, level="direct", version="v1", pattern=None, **kw):
    return Mapping(id=i, chamber="house", committee_code=committee, subcommittee_code=sub, committee_name=kw.get("name", f"Committee {committee}"),
                   subcommittee_name=f"Sub {sub}" if sub else None, sic_start=start, sic_end=end, industry_pattern=pattern, relevance_level=level,
                   rationale=f"why {i}", jurisdiction_text="official text", source_citation="Rule X 1(c)", source_url=SRC, reviewed_at=None, mapping_version=version)


def A(committee="AS00", sub=None, name=None):
    return Assignment(committee, name or f"Committee {committee}", sub, f"Sub {sub}" if sub else None)


# --- core matching --------------------------------------------------------------------------------------------

def test_a_direct_committee_match_returns_the_full_provenance():
    r = CommitteeIndustryMatcher([M(1)]).evaluate([A()], "3721", "Aircraft")
    assert (r.status, r.reason, r.level, r.mapping_version) == ("relevant", "match", "direct", "v1")
    m = r.primary
    assert (m.committee_code, m.committee_name, m.subcommittee_code, m.scope, m.sic_range, m.rationale) == ("AS00", "Committee AS00", None, "committee", "3720-3729", "why 1")
    assert (m.source_citation, m.source_url, m.jurisdiction_text, m.mapping_version, m.reviewed, m.mapping_id) == ("Rule X 1(c)", SRC, "official text", "v1", False, 1)


def test_an_unrelated_industry_is_not_relevant_when_every_committee_is_mapped():
    r = CommitteeIndustryMatcher([M(1)]).evaluate([A()], "6021", "National Commercial Banks")
    assert (r.status, r.reason, r.matches, r.unmapped_committees) == ("not_relevant", "no_match", [], [])


def test_sic_range_edges_are_inclusive():
    m = CommitteeIndustryMatcher([M(1, start=3720, end=3729)])
    assert [m.evaluate([A()], str(c)).status for c in (3719, 3720, 3729, 3730)] == ["not_relevant", "relevant", "relevant", "not_relevant"]


def test_a_subcommittee_mapping_applies_only_to_members_of_that_subcommittee():
    rows = [M(1, committee="AS00", sub="AS28", start=3730, end=3732)]
    on_sub = [A("AS00"), A("AS00", "AS28")]
    off_sub = [A("AS00"), A("AS00", "AS25")]
    matcher = CommitteeIndustryMatcher(rows)
    assert matcher.evaluate(on_sub, "3731").status == "relevant" and matcher.evaluate(off_sub, "3731").status == "not_relevant"


def test_a_broad_parent_mapping_applies_to_a_member_on_any_of_its_subcommittees():
    r = CommitteeIndustryMatcher([M(1)]).evaluate([A("AS00", "AS25")], "3721")
    assert r.status == "relevant" and r.primary.scope == "committee"


def test_a_subcommittee_mapping_is_preferred_over_the_parent_even_when_the_parent_is_stronger():
    parent = M(1, level="direct", start=3720, end=3729)
    sub = M(2, sub="AS25", level="related", start=3720, end=3729)
    r = CommitteeIndustryMatcher([parent, sub]).evaluate([A("AS00"), A("AS00", "AS25")], "3721")
    assert [m.mapping_id for m in r.matches] == [2, 1] and r.primary.scope == "subcommittee" and r.level == "related"


def test_overlapping_mappings_are_all_reported_in_a_fixed_order():
    rows = [M(5, committee="PW00", level="related", start=3700, end=3799), M(3, committee="AS00", level="direct", start=3720, end=3729),
            M(4, committee="SY00", level="direct", start=3721, end=3721), M(2, committee="FA00", level="direct", start=3720, end=3729)]
    seats = [A("AS00"), A("PW00"), A("SY00"), A("FA00")]
    r = CommitteeIndustryMatcher(rows).evaluate(seats, "3721")
    assert [m.mapping_id for m in r.matches] == [4, 2, 3, 5]  # direct before related, narrower range first, then id
    assert r.primary.committee_code == "SY00"


def test_none_means_the_committee_was_reviewed_and_has_no_industry_jurisdiction():
    rows = [M(1, committee="RU00", start=None, end=None, level="none"), M(2)]
    matcher = CommitteeIndustryMatcher(rows)
    assert matcher.evaluate([A("RU00")], "3721").status == "not_relevant"  # mapped, nothing matches
    assert matcher.evaluate([A("RU00"), A("AS00")], "3721").status == "relevant"


# --- unknowns -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("sic", [None, "", "  ", "abc", "0000", "372", "37210", 0, "37 21"])
def test_missing_or_unusable_sic_is_unknown_even_when_a_mapping_would_otherwise_match(sic):
    r = CommitteeIndustryMatcher([M(1, start=1, end=9999)]).evaluate([A()], sic, "Aircraft")
    assert (r.status, r.reason, r.matches) == ("unknown", "no_sic", [])


def test_a_politician_with_no_committee_assignments_is_unknown():
    r = CommitteeIndustryMatcher([M(1)]).evaluate([], "3721")
    assert (r.status, r.reason) == ("unknown", "no_committee_assignments")


def test_a_committee_with_no_mapping_is_unknown_and_named():
    r = CommitteeIndustryMatcher([M(1)]).evaluate([A("ZZ00", name="Committee on Imaginary Affairs")], "3721")
    assert (r.status, r.reason, r.unmapped_committees) == ("unknown", "unmapped_committees", ["Committee on Imaginary Affairs"])


def test_an_unmapped_committee_prevents_asserting_not_relevant_but_not_a_found_match():
    matcher = CommitteeIndustryMatcher([M(1)])
    partial_no_match = matcher.evaluate([A("AS00"), A("ZZ00", name="Unmapped")], "6021")
    assert (partial_no_match.status, partial_no_match.reason) == ("unknown", "unmapped_committees")  # the unmapped one might be relevant
    partial_match = matcher.evaluate([A("AS00"), A("ZZ00", name="Unmapped")], "3721")
    assert partial_match.status == "relevant" and partial_match.unmapped_committees == ["Unmapped"]


def test_no_mappings_at_all_means_everything_is_unknown_not_not_relevant():
    r = CommitteeIndustryMatcher([]).evaluate([A()], "3721")
    assert (r.status, r.reason) == ("unknown", "unmapped_committees") and r.mapping_version is None


# --- patterns, determinism, versions --------------------------------------------------------------------------

def test_an_industry_pattern_narrows_a_range_and_needs_the_description():
    assert CommitteeIndustryMatcher([M(1, start=6000, end=6999, pattern=r"\bbank")]).evaluate([A()], "6021", "National Commercial Banks").status == "relevant"
    assert CommitteeIndustryMatcher([M(1, start=6000, end=6999, pattern="bank")]).evaluate([A()], "6021", "National Commercial Banks").status == "relevant"
    assert CommitteeIndustryMatcher([M(1, start=6000, end=6999, pattern="bank")]).evaluate([A()], "6021", None).status == "not_relevant"
    assert CommitteeIndustryMatcher([M(1, start=6000, end=6999, pattern="bank")]).evaluate([A()], "6331", "Fire, Marine & Casualty Insurance").status == "not_relevant"


def test_results_are_deterministic_and_independent_of_input_order():
    rows = [M(i, committee=c, start=3700 + i, end=3800) for i, c in enumerate(["AS00", "PW00", "SY00", "FA00", "HM00"], start=1)]
    seats = [A(c) for c in ("AS00", "PW00", "SY00", "FA00", "HM00")]
    base = CommitteeIndustryMatcher(rows).evaluate(seats, "3750")
    for _ in range(5):
        assert CommitteeIndustryMatcher(list(reversed(rows))).evaluate(list(reversed(seats)), "3750") == base
    assert CommitteeIndustryMatcher(rows).evaluate(seats, "3750") == base


def test_the_matcher_uses_one_mapping_version_and_defaults_to_the_most_recently_loaded():
    rows = [M(1, version="v1", start=3720, end=3729), M(2, version="v2", start=6000, end=6099)]
    latest = CommitteeIndustryMatcher(rows)
    assert latest.version == "v2" and latest.evaluate([A()], "3721").status == "not_relevant" and latest.evaluate([A()], "6021").primary.mapping_version == "v2"
    old = CommitteeIndustryMatcher(rows, version="v1")
    assert old.evaluate([A()], "3721").primary.mapping_version == "v1" and old.evaluate([A()], "6021").status == "not_relevant"


def test_the_matcher_has_no_network_or_language_model_dependency():
    import poltracker.committee_industry as mod

    tree = ast.parse(Path(mod.__file__).read_text())
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"httpx", "requests", "urllib", "socket", "openai", "anthropic", "aiohttp"}


def test_evaluation_never_touches_the_network(monkeypatch):
    import socket

    def blocked(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", blocked)
    assert CommitteeIndustryMatcher([M(1)]).evaluate([A()], "3721").status == "relevant"


# --- loading, validation, versioning in the database -----------------------------------------------------------

def row(**kw):
    base = dict(chamber="house", committee_code="AS00", subcommittee_code=None, committee_name="Armed Services", subcommittee_name=None, sic_start="3720", sic_end="3729",
                industry_pattern=None, relevance_level="direct", rationale="r", jurisdiction_text="t", source_citation="c", source_url=SRC, reviewed_at=None, mapping_version="v1",
                review_status="needs_review", reviewed_by=None, review_note=None, jurisdiction_basis="rule_x_text")
    return {**base, **kw}


def write(tmp_path, rows, name="m.json"):
    p = tmp_path / name
    p.write_text(json.dumps(rows))
    return p


def test_sync_loads_rows_idempotently_and_replaces_only_the_same_version(session_factory, tmp_path):
    v1 = write(tmp_path, [row(), row(committee_code="BA00", sic_start="6000", sic_end="6099")])
    v2 = write(tmp_path, [row(mapping_version="v2")], "v2.json")
    with session_factory() as s:
        assert sync_mappings(s, v1) == ("v1", 2)
        assert sync_mappings(s, v1) == ("v1", 2)  # again: replaced, not duplicated
        sync_mappings(s, v2)
        s.commit()
        assert s.scalar(select(func.count(CommitteeIndustryMapping.id))) == 3
        assert [m.mapping_version for m in load_mappings(s)] == ["v1", "v1", "v2"] and len(load_mappings(s, "v1")) == 2
        assert CommitteeIndustryMatcher(load_mappings(s)).version == "v2"
        sync_mappings(s, write(tmp_path, [row(sic_start="3000", sic_end="3999")], "v1b.json"))  # a revised v1 replaces the old v1 rows only
        s.commit()
        assert len(load_mappings(s, "v1")) == 1 and len(load_mappings(s, "v2")) == 1


@pytest.mark.parametrize("bad,why", [
    ([], "non-empty"), ("x", "non-empty"),
    ([row(relevance_level="suspicious")], "relevance_level"),
    ([row(sic_start="3729", sic_end="3720")], "start <= end"), ([row(sic_start="abc")], "4-digit"), ([row(sic_end=None)], "4-digit"),
    ([row(relevance_level="none")], "no SIC range"),
    ([row(rationale="")], "missing rationale"), ([row(source_url=" ")], "missing source_url"), ([row(committee_code=None)], "missing committee_code"),
    ([row(), row(mapping_version="v2")], "exactly one mapping_version"),
    ([row(industry_pattern="(")], "regex"), ([row(subcommittee_code="AS25")], "subcommittee_name"),
])
def test_invalid_mapping_files_are_rejected_and_nothing_is_loaded(session_factory, tmp_path, bad, why):
    with session_factory() as s:
        with pytest.raises(MappingError, match=why.split()[0]):
            sync_mappings(s, write(tmp_path, bad))
        s.rollback()
        assert s.scalar(select(func.count(CommitteeIndustryMapping.id))) == 0


def test_an_unreadable_file_is_a_mapping_error(tmp_path):
    with pytest.raises(MappingError, match="cannot read"):
        load_rows(tmp_path / "missing.json")


def test_a_none_row_may_have_no_range_and_reviewed_at_is_preserved(session_factory, tmp_path):
    rows = [row(committee_code="RU00", relevance_level="none", sic_start=None, sic_end=None, reviewed_at="2026-10-08T00:00:00", review_status="reviewed", reviewed_by="J. Reviewer")]
    with session_factory() as s:
        sync_mappings(s, write(tmp_path, rows))
        (m,) = load_mappings(s)
        assert (m.relevance_level, m.sic_start, m.reviewed_at, m.review_status, m.reviewed_by) == ("none", None, __import__("datetime").datetime(2026, 10, 8), "reviewed", "J. Reviewer")


# --- the shipped mapping file ------------------------------------------------------------------------------------

REAL = ROOT / "data" / "committee_industry_mappings.json"
SIC = json.loads((ROOT / "data" / "sic_codes.json").read_text())["codes"]
KNOWN_COMMITTEES = {"AG00", "AP00", "AS00", "BA00", "BU00", "EC00", "ED00", "FA00", "GO00", "HA00", "HM00", "IF00", "IG00", "II00", "IT00", "JL00", "JP00",
                    "JU00", "PW00", "QJ00", "RU00", "SM00", "SO00", "SY00", "VR00", "WM00", "ZS00"}


def real_matcher():
    rows = load_rows(REAL)
    maps = [Mapping(i, r["chamber"], r["committee_code"], r.get("subcommittee_code"), r["committee_name"], r.get("subcommittee_name"), parse_sic(r.get("sic_start")),
                    parse_sic(r.get("sic_end")), r.get("industry_pattern"), r["relevance_level"], r["rationale"], r.get("jurisdiction_text"), r.get("source_citation"),
                    r["source_url"], None, r["mapping_version"]) for i, r in enumerate(rows, start=1)]
    return CommitteeIndustryMatcher(maps), rows


def test_the_shipped_mapping_file_is_valid_complete_and_cited():
    matcher, rows = real_matcher()
    validate_rows(rows)
    assert {r["mapping_version"] for r in rows} == {"2026.1-draft"} and all((r["reviewed_at"] is not None) == (r["review_status"] == "reviewed") for r in rows)  # reviewed_at set exactly for reviewed rows
    assert matcher.mapped_committees == KNOWN_COMMITTEES  # every committee POLTRACKER tracks has an explicit decision
    for r in rows:
        assert r["source_url"].startswith("https://") and r["rationale"].strip() and r["source_citation"] and r["jurisdiction_text"]
        if r["subcommittee_code"]:
            assert r["subcommittee_code"][:2] == r["committee_code"][:2] and r["subcommittee_name"]
        if r["relevance_level"] == "none":
            assert r["sic_start"] is None
        else:
            a, b = int(r["sic_start"]), int(r["sic_end"])
            # The SEC table omits agricultural codes (Division A, 0100-0999) because it lists only codes assigned to registrants.
            assert a < 1000 or any(a <= int(c) <= b for c in SIC), f"{r['committee_code']} {a}-{b} covers no official SIC code"
            assert "Official SIC titles in" in r["rationale"]


def rel(seats, sic, desc=None):
    return real_matcher()[0].evaluate(seats, sic, desc)


@pytest.mark.parametrize("seats,sic,level", [
    ([A("AS00")], "3760", "direct"),   # guided missiles: Armed Services
    ([A("AS00")], "3812", "related"),   # defense electronics: downgraded in round 2 (one SIC code mixes defense and consumer navigation)
    ([A("AS00")], "3730", "direct"),   # shipbuilding
    ([A("BA00")], "6021", "direct"),   # commercial banks: Financial Services
    ([A("BA00")], "6331", "direct"),   # insurance
    ([A("AG00")], "0100", "direct"),   # crops: Agriculture
    ([A("PW00")], "4011", "direct"),   # railroads: Transportation and Infrastructure
    ([A("PW00")], "4512", "direct"),   # airlines
    ([A("IF00", "IF03")], "1311", "direct"),  # oil and gas: Energy and Commerce Energy
    ([A("IF00")], "4813", "direct"),   # telephone communications
    ([A("IF00", "IF14")], "2834", "direct"),  # pharma: E&C Health
    ([A("WM00", "WM02")], "8062", "related"),  # hospitals: Ways and Means Health, downgraded in round 2
    ([A("II00")], "1040", "direct"),   # gold and silver ores: Natural Resources
])
def test_known_core_relationships_hold_in_the_shipped_mappings(seats, sic, level):
    r = rel(seats, sic)
    assert (r.status, r.level) == ("relevant", level)


@pytest.mark.parametrize("seats,sic,why", [
    ([A("WM00")], "3721", "economy-wide committee, no industry mapping"),
    ([A("RU00")], "6021", "Rules"), ([A("SO00")], "6021", "Ethics"), ([A("BU00")], "6021", "Budget"), ([A("SM00")], "6021", "Small Business"),
    ([A("AS00")], "6021", "banks are not Armed Services jurisdiction"), ([A("AG00")], "3760", "missiles are not Agriculture"),
])
def test_economy_wide_and_unrelated_pairs_are_not_relevant(seats, sic, why):
    assert rel(seats, sic).status == "not_relevant", why


@pytest.mark.parametrize("seats,sic,desc", [
    ([A("AG00"), A("AG00", "AG22")], "6211", "Security Brokers, Dealers & Flotation"),   # an equities exchange is not "commodity markets"
    ([A("AG00"), A("AG00", "AG22")], "6200", "Security & Commodity Brokers"),
    ([A("AG00"), A("AG00", "AG03")], "2086", "Bottled & Canned Soft Drinks"),              # beverages are not "human nutrition"
    ([A("AS00"), A("AS00", "AS35")], "7374", "Services-Computer Processing & Data"),       # payroll processing is not DoD cyber
    ([A("JU00"), A("JU00", "JU03")], "7374", "Services-Computer Processing & Data"),
    ([A("BA00")], "6794", "Patent Owners & Lessors"),                                      # patent licensing is not Financial Services
    ([A("PW00")], "4724", "Travel Agencies"),                                              # travel agencies are not transportation infrastructure
    ([A("PW00"), A("PW00", "PW02")], "4953", "Refuse Systems"),                            # waste hauling is not water resources
    ([A("SY00"), A("SY00", "SY15")], "3829", "Measuring & Controlling Devices"),           # general instruments are too loosely tied to NIST
])
def test_regression_each_false_positive_found_in_manual_review_stays_fixed(seats, sic, desc):
    assert rel(seats, sic, desc).status != "relevant"


def test_a_subcommittee_seat_gives_the_narrower_mapping_precedence_in_the_shipped_file():
    r = rel([A("AS00"), A("AS00", "AS28")], "3730", "Ship & Boat Building & Repairing")
    assert r.primary.scope == "subcommittee" and r.primary.subcommittee_code == "AS28" and any(m.scope == "committee" for m in r.matches)


# --- measurement over trades (read-only) ------------------------------------------------------------------------

def seed_universe(sf, tmp_path):
    with sf() as s:
        armed = Politician(canonical_key="house:a", name="Armed Member", chamber="house")
        bank = Politician(canonical_key="house:b", name="Banking Member", chamber="house")
        rules = Politician(canonical_key="house:c", name="Rules Member", chamber="house")
        nocomm = Politician(canonical_key="senate:d", name="Senator", chamber="senate")
        s.add_all([armed, bank, rules, nocomm])
        secs = {t: Security(ticker=t, sic_code=c, industry=i) for t, c, i in
                [("LMT", "3721", "Aircraft"), ("BAC", "6021", "National Commercial Banks"), ("NOSIC", None, None), ("PEP", "2086", "Soft Drinks")]}
        s.add_all(secs.values())
        s.flush()
        for pol, code, name in [(armed, "AS00", "Committee on Armed Services"), (bank, "BA00", "Committee on Financial Services"), (rules, "RU00", "Committee on Rules")]:
            s.add(CommitteeAssignment(politician_id=pol.id, committee_name=name, committee_code=code, subcommittee_code="", role="Member", chamber="house", source="t"))
        n = 0
        for pol in (armed, bank, rules, nocomm):
            for t, sec in secs.items():
                n += 1
                s.add(Trade(source="t", fingerprint=f"f{n}", politician_id=pol.id, security_id=sec.id, politician_name=pol.name, chamber=pol.chamber, ticker=t,
                            transaction_type="buy", transaction_date=date(2026, 5, 1)))
        s.commit()
        sync_mappings(s, write(tmp_path, [row(), row(committee_code="BA00", committee_name="Financial Services", sic_start="6000", sic_end="6099"),
                                          row(committee_code="RU00", committee_name="Rules", relevance_level="none", sic_start=None, sic_end=None)]))
        s.commit()


def snap(sf):
    with sf() as s:
        return [s.execute(text(f"select * from {t} order by 1")).all() for t in ("trades", "securities", "politicians", "committee_assignments")]


def test_the_report_counts_every_outcome_and_writes_nothing(session_factory, tmp_path):
    seed_universe(session_factory, tmp_path)
    before = snap(session_factory)
    r = evaluate_trades(session_factory)
    assert snap(session_factory) == before
    assert (r.trades_total, r.securities_total, r.securities_with_sic, r.politicians_total, r.politicians_with_assignments) == (16, 4, 3, 4, 3)
    assert (r.relevant, r.relevant_direct, r.relevant_related_only) == (2, 2, 0)  # Armed Member x LMT, Banking Member x BAC
    assert r.unknown_no_sic == 4 and r.unknown_no_assignments == 3 and r.unknown_unmapped == 0
    assert r.not_relevant == 16 - 2 - 4 - 3 and r.evaluable == r.relevant + r.not_relevant
    assert r.by_committee["AS00 Armed Services [committee]"] == 1


def test_trades_of_a_politician_on_an_unmapped_committee_are_unknown_and_counted_by_committee(session_factory, tmp_path):
    seed_universe(session_factory, tmp_path)
    with session_factory() as s:
        pol = s.scalar(select(Politician).where(Politician.name == "Rules Member"))
        s.add(CommitteeAssignment(politician_id=pol.id, committee_name="Committee on Imaginary Affairs", committee_code="ZZ00", subcommittee_code="", role="Member", chamber="house", source="t"))
        s.commit()
    r = evaluate_trades(session_factory)
    assert r.unknown_unmapped == 3 and r.unmapped_committees["Committee on Imaginary Affairs"] == 3  # the no-SIC trade is unknown for a different reason


def test_the_assignment_loader_reads_committee_and_subcommittee_seats(session_factory, tmp_path):
    seed_universe(session_factory, tmp_path)
    with session_factory() as s:
        pid = s.scalar(select(Politician.id).where(Politician.name == "Armed Member"))
        s.add(CommitteeAssignment(politician_id=pid, committee_name="Committee on Armed Services", committee_code="AS00", subcommittee_name="Seapower", subcommittee_code="AS28", role="Member", chamber="house", source="t"))
        s.commit()
        seats = load_assignments(s, pid)
    assert {(a.committee_code, a.subcommittee_code) for a in seats} == {("AS00", None), ("AS00", "AS28")}


def test_a_low_numbered_sic_code_still_matches_after_parsing_once():
    """Agricultural codes such as 0100 are below 1000; they must survive the internal parse (a regression found during the review pass)."""
    m = CommitteeIndustryMatcher([M(1, committee="AG00", start=100, end=299)])
    assert m.evaluate([A("AG00")], "0100").status == "relevant" and [r.id for r in m.applicable_rows([A("AG00")], "0100")] == [1]
