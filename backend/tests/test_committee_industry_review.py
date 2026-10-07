"""The mapping review format and the review packet: exact counts on a small known universe, honest status, read-only."""

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from poltracker import committee_industry_review as rv
from poltracker.committee_industry import MappingError, load_mappings, load_rows, sync_mappings, validate_rows
from poltracker.models import CommitteeAssignment, Politician, Security, Trade

ROOT = Path(__file__).resolve().parents[2]
REAL = ROOT / "data" / "committee_industry_mappings.json"
SIC = {"3721": "AIRCRAFT", "3724": "AIRCRAFT ENGINES & ENGINE PARTS", "3760": "GUIDED MISSILES & SPACE VEHICLES", "6021": "NATIONAL COMMERCIAL BANKS",
       "6324": "HOSPITAL & MEDICAL SERVICE PLANS", "6331": "FIRE, MARINE & CASUALTY INSURANCE", "2834": "PHARMACEUTICAL PREPARATIONS"}


def mrow(code, start, end, level="direct", sub=None, basis="rule_x_text", note=None, name=None, status="needs_review", **kw):
    r = dict(chamber="house", committee_code=code, subcommittee_code=sub, committee_name=name or f"Committee {code}", subcommittee_name=f"Sub {sub}" if sub else None,
             sic_start=start, sic_end=end, industry_pattern=None, relevance_level=level, rationale=f"why {code} {start}", jurisdiction_text="official wording",
             source_citation="Rule X", source_url="https://example.gov/x", reviewed_at=None, mapping_version="t1", review_status=status, reviewed_by=None,
             review_note=note, jurisdiction_basis=basis)
    r.update(kw)
    return r


# --- the review fields in the mapping format -------------------------------------------------------------------

def test_shipped_review_status_is_consistent_and_limited_to_the_round_1_decisions():
    rows = load_rows(REAL)
    assert len(rows) == 191
    reviewed = [r for r in rows if r["review_status"] == "reviewed"]
    assert len(reviewed) == 47 and len(rows) - len(reviewed) == 144
    assert all((r["review_status"] == "reviewed") == (r["reviewed_at"] is not None) for r in rows)
    assert all(r["reviewed_by"] and r["review_note"] for r in reviewed)  # every reviewed row says who decided and why
    assert all(r["reviewed_by"] is None for r in rows if r["review_status"] == "needs_review")
    assert {r["jurisdiction_basis"] for r in rows} <= {"rule_x_text", "committee_published_text", "subcommittee_name", "committee_name"}


def test_the_shipped_basis_matches_what_was_actually_read():
    rows = load_rows(REAL)
    subs = [r for r in rows if r["subcommittee_code"]]
    assert {r["jurisdiction_basis"] for r in subs if r["committee_code"] != "PW00"} == {"subcommittee_name"}  # only Transportation publishes subcommittee text
    assert {r["jurisdiction_basis"] for r in subs if r["committee_code"] == "PW00"} == {"committee_published_text"}
    committee_level = {r["committee_code"]: r["jurisdiction_basis"] for r in rows if not r["subcommittee_code"]}
    assert committee_level["AS00"] == "rule_x_text" and committee_level["BA00"] == "rule_x_text"
    assert committee_level["RU00"] == "committee_name" and committee_level["IG00"] == "committee_name"  # Rule X wording was not read for these


@pytest.mark.parametrize("change,message", [
    (dict(review_status="approved"), "review_status"),
    (dict(review_status="reviewed"), "reviewed_at must be set"),  # reviewed needs a date
    (dict(reviewed_at="2026-10-08T00:00:00"), "reviewed_at must be set"),  # a needs_review row is never dated
    (dict(jurisdiction_basis="guess"), "jurisdiction_basis"),
    (dict(jurisdiction_basis=None), "jurisdiction_basis"),
    (dict(review_status=None), "review_status"),
])
def test_invalid_review_fields_are_rejected(change, message):
    with pytest.raises(MappingError, match=message):
        validate_rows([mrow("AS00", "3720", "3729", **change)])


def test_a_properly_reviewed_row_is_accepted_and_round_trips_through_the_database(session_factory, tmp_path):
    rows = [mrow("AS00", "3720", "3729", status="reviewed", reviewed_at="2026-10-08T09:00:00", reviewed_by="J. Reviewer", review_note="approved as written"),
            mrow("BA00", "6000", "6099", basis="subcommittee_name", note="Review history: x")]
    path = tmp_path / "m.json"
    path.write_text(json.dumps(rows))
    with session_factory() as s:
        sync_mappings(s, path)
        s.commit()
        a, b = load_mappings(s)
    assert (a.review_status, a.reviewed_by, a.review_note, a.reviewed_at.isoformat(), a.jurisdiction_basis) == ("reviewed", "J. Reviewer", "approved as written", "2026-10-08T00:00:00".replace("00:00:00", "09:00:00"), "rule_x_text")
    assert (b.review_status, b.reviewed_at, b.jurisdiction_basis, b.explicitly_verified, a.explicitly_verified) == ("needs_review", None, "subcommittee_name", False, True)


# --- the packet, on a small known universe ----------------------------------------------------------------------

@pytest.fixture
def universe(session_factory):
    with session_factory() as s:
        armed = Politician(canonical_key="house:a", name="Armed Person", chamber="house")
        armed2 = Politician(canonical_key="house:a2", name="Second Armed Person", chamber="house")
        bank = Politician(canonical_key="house:b", name="Banker Person", chamber="house")
        s.add_all([armed, armed2, bank])
        secs = {t: Security(ticker=t, sic_code=c, industry=i) for t, c, i in [
            ("BA", "3721", "Aircraft"), ("RTX", "3724", "Aircraft Engines & Engine Parts"), ("LMT", "3760", "Guided Missiles"), ("JPM", "6021", "National Commercial Banks"),
            ("UNH", "6324", "Hospital & Medical Service Plans"), ("BRK", "6331", "Fire, Marine & Casualty Insurance"), ("PFE", "2834", "Pharmaceutical Preparations")]}
        s.add_all(secs.values())
        s.flush()
        for pol, code in [(armed, "AS00"), (armed2, "AS00"), (bank, "BA00")]:
            s.add(CommitteeAssignment(politician_id=pol.id, committee_name=f"Committee {code}", committee_code=code, subcommittee_code="", role="Member", chamber="house", source="t"))
        s.add(CommitteeAssignment(politician_id=armed.id, committee_name="Committee AS00", committee_code="AS00", subcommittee_name="Sub AS25", subcommittee_code="AS25", role="Member", chamber="house", source="t"))
        n = 0
        for pol, tickers in [(armed, ["BA", "RTX", "LMT", "JPM"]), (armed2, ["BA", "BA"]), (bank, ["JPM", "UNH", "BRK", "BA", "PFE"])]:
            for t in tickers:
                n += 1
                s.add(Trade(source="t", fingerprint=f"f{n}", politician_id=pol.id, security_id=secs[t].id, politician_name=pol.name, chamber="house", ticker=t,
                            transaction_type="buy", transaction_date=date(2026, 5, 1)))
        s.commit()
    return session_factory


ROWS = [
    mrow("AS00", "3720", "3729", name="Armed Services"),                                              # 1: committee, direct: BA, RTX
    mrow("AS00", "3720", "3729", sub="AS25", basis="subcommittee_name", name="Armed Services"),        # 2: subcommittee, same range (preferred for armed)
    mrow("AS00", "3760", "3769", level="related", name="Armed Services"),                              # 3: related: LMT
    mrow("BA00", "6000", "6099", name="Financial Services"),                                           # 4: banks: JPM
    mrow("BA00", "6300", "6499", name="Financial Services"),                                           # 5: insurance: UNH (632), BRK (633) -> mixed groups
    mrow("PW00", "3700", "3899", level="related", name="Transportation", note="Review history: narrowed after a false positive."),  # 6: broad (199 codes) + overlaps AS00, no members
    mrow("RU00", None, None, level="none", name="Rules", basis="committee_name"),                      # 7: none
    mrow("IF00", "9990", "9999", name="Energy and Commerce"),                                          # 8: matches no security
]


def review(universe):
    return rv.build_review(universe, ROWS, SIC)


def rep(r, key):
    return next(x for x in r.rows if x.key == key)


def test_per_row_security_trade_and_politician_counts_are_exact(universe):
    r = review(universe)
    r1, r2, r3 = rep(r, "AS00:3720-3729:direct"), rep(r, "AS00/AS25:3720-3729:direct"), rep(r, "AS00:3760-3769:related")
    assert (r1.securities_matched, r1.example_tickers) == (2, ["BA", "RTX"])
    assert (r1.trades_matched, r1.politicians_matched) == (4, 2)  # armed: BA, RTX; armed2: BA, BA. The banker has no Armed Services seat.
    assert (r2.trades_matched, r2.politicians_matched) == (2, 1)  # only the member who sits on subcommittee AS25
    assert (r1.trades_primary, r2.trades_primary) == (2, 2)  # for armed the subcommittee row takes precedence, so the parent is primary only for armed2
    assert (r3.securities_matched, r3.trades_matched, r3.trades_primary) == (1, 1, 1)
    assert rep(r, "BA00:6000-6099:direct").trades_matched == 1 and rep(r, "BA00:6000-6099:direct").securities_matched == 1  # only the banker has the BA00 seat


def test_summary_statistics_and_trade_effects(universe):
    s = rv._summary(review(universe))
    assert (s["mappings"], s["direct"], s["related"], s["none"]) == (8, 5, 2, 1)
    assert (s["committee_level"], s["subcommittee_level"]) == (7, 1)
    assert (s["explicit_jurisdiction"], s["inferred_subcommittee_name"], s["inferred_committee_name"]) == (6, 1, 1)
    assert (s["needs_review"], s["reviewed"]) == (8, 0)
    # trades with a match: armed BA, RTX, LMT (3), armed2 BA x2 (2), banker JPM, UNH, BRK (3) = 8 of 11; the banker's BA and PFE match nothing
    assert (s["trades_total"], s["trades_with_any_match"]) == (11, 8)
    assert (s["trades_with_a_direct_match"], s["trades_with_related_only_matches"]) == (7, 1)  # only armed's LMT trade is related-only
    assert (s["rows_matching_no_current_security"], s["rows_matching_no_current_trade"]) == (1, 2)  # IF00 9990-9999 matches nothing; PW00 has no member


def test_scrutiny_flags_are_computed_from_the_data_not_hand_written(universe, monkeypatch):
    monkeypatch.setattr(rv, "MANY_TRADES", 4)
    r = review(universe)
    assert "many_matches" in rep(r, "AS00:3720-3729:direct").flags and "many_matches" not in rep(r, "AS00/AS25:3720-3729:direct").flags
    assert {"inferred_from_name"} <= set(rep(r, "AS00/AS25:3720-3729:direct").flags)
    assert "inferred_from_name" not in rep(r, "AS00:3720-3729:direct").flags  # explicitly verified committee text
    assert "related_level" in rep(r, "AS00:3760-3769:related").flags
    assert {"broad_range", "overlaps_other_committee", "false_positive_history", "related_level"} <= set(rep(r, "PW00:3700-3899:related").flags)
    ins = rep(r, "BA00:6300-6499:direct")
    assert {"broad_range", "mixed_industries"} <= set(ins.flags) and set(ins.mixed_groups) == {"632", "633"}  # health plans and casualty insurers are different groups
    assert "overlaps_other_committee" in rep(r, "AS00:3720-3729:direct").flags and rep(r, "AS00:3720-3729:direct").overlaps == ["PW00 3700-3899 (related)"]
    assert rep(r, "RU00:none:none").flags == ["inferred_from_name"]
    assert rep(r, "IF00:9990-9999:direct").flags == []


def test_the_markdown_packet_shows_every_required_element_for_every_row(universe):
    md = rv.render_markdown(review(universe))
    for needle in ["Armed Services", "Sub AS25", "3720-3729", "Official SIC titles covered", "3721 Aircraft", "why AS00 3720", "Official jurisdiction wording used", "official wording",
                   "https://example.gov/x", "explicitly verified (official wording read)", "inferred from the subcommittee name, not verified",
                   "inferred from the committee name, not verified", "In POLTRACKER data", "2 securities", "Trades matched", "needs_review",
                   "Top 20 mappings by number of affected trades", "Priority: rows with a substantive concern", "more than one industry group",
                   "Decision:", "No row has been reviewed", "Review note", "none (reviewed as having no industry-specific jurisdiction)"]:
        assert needle in md, needle
    assert md.count("#### `") == 8 and "### AS00:" in md and "### PW00:" in md


def test_top_twenty_is_ordered_by_trades_matched_and_excludes_none_rows(universe):
    md = rv.render_markdown(review(universe))
    top = md.split("## Top 20 mappings")[1].split("## Rows that deserve")[0]
    lines = [l for l in top.splitlines() if l.startswith("| ") and l[2].isdigit()]
    counts = [int(l.split("|")[4]) for l in lines]
    assert counts == sorted(counts, reverse=True) and "RU00" not in top and len(lines) <= 20


def test_a_row_with_a_priority_concern_is_in_the_priority_table_and_routine_rows_are_not(universe):
    md = rv.render_markdown(review(universe))
    priority = md.split("### Priority")[1].split("### Routine")[0]
    assert "BA00:6300-6499:direct" in priority and "PW00:3700-3899:related" in priority and "AS00/AS25:3720-3729:direct" not in priority


def test_the_packet_is_deterministic_read_only_and_never_names_a_politician(universe):
    def snap():
        with universe() as s:
            return [s.execute(text(f"select * from {t} order by 1")).all() for t in ("trades", "securities", "politicians", "committee_assignments")]

    before = snap()
    first, second = rv.render_markdown(review(universe)), rv.render_markdown(review(universe))
    assert first == second and snap() == before
    assert "Armed Person" not in first and "Banker Person" not in first and "Second Armed" not in first


def test_generating_the_packet_does_not_modify_or_review_the_mapping_file(universe, tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(ROWS))
    sha = lambda: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
    before = sha()
    rv.build_review(universe, load_rows(path), SIC)
    assert sha() == before and all(r["review_status"] == "needs_review" for r in json.loads(path.read_text()))


def test_the_shipped_mappings_produce_a_complete_packet_on_an_empty_database(session_factory):
    review_ = rv.build_review(session_factory, load_rows(REAL), json.loads((ROOT / "data" / "sic_codes.json").read_text())["codes"])
    md = rv.render_markdown(review_)
    assert md.count("#### `") == 191 and review_.trades_total == 0 and "| Mappings | 191 |" in md


# --- the priority-row review table ---------------------------------------------------------------------------------

RECS = {
    "AS00:3720-3729:direct": ("APPROVE DIRECT", "squarely defense"),
    "AS00/AS25:3720-3729:direct": ("SPLIT RANGE", "x"),
    "AS00:3760-3769:related": ("KEEP RELATED", "context only"),
    "BA00:6000-6099:direct": ("APPROVE DIRECT", "banks"),
    "BA00:6300-6499:direct": ("SPLIT RANGE", "move health plans"),
    "PW00:3700-3899:related": ("REMOVE", "too broad"),
}


def recs(**changes):
    out = {k: {"key": k, "action": a, "reason": why} for k, (a, why) in RECS.items()}
    out.update(changes)
    return out


@pytest.fixture
def small_review(universe, monkeypatch):
    monkeypatch.setattr(rv, "MANY_TRADES", 2)  # make a few rows "many matches" so the priority set is non-trivial
    return rv.build_review(universe, ROWS, SIC)


def test_priority_rows_are_ordered_direct_first_then_trades_then_broad_mixed(small_review):
    keys = [r.key for r in rv.priority_rows(small_review)]
    levels = [rep(small_review, k).mapping.relevance_level for k in keys]
    assert levels == sorted(levels, key=lambda lv: rv.LEVEL_ORDER[lv])  # every direct row precedes every related row
    direct_trades = [rep(small_review, k).trades_matched for k in keys if rep(small_review, k).mapping.relevance_level == "direct"]
    assert direct_trades == sorted(direct_trades, reverse=True)
    assert "RU00:none:none" not in keys and "IF00:9990-9999:direct" not in keys  # no substantive concern


def test_the_priority_table_renders_every_required_column_for_every_priority_row(small_review):
    keys = [r.key for r in rv.priority_rows(small_review)]
    table = rv.render_priority_table(small_review, {k: v for k, v in recs().items() if k in keys})
    head = [l for l in table.splitlines() if l.startswith("| #")][0]
    for col in ["Committee / subcommittee", "SIC range", "SIC titles covered", "Level", "Basis", "Official wording", "Trades", "Example tickers", "Overlaps", "Recommended action"]:
        assert col in head
    body = [l for l in table.splitlines() if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    assert len(body) == len(keys) and "Nothing here changes a mapping" in table
    assert "**APPROVE DIRECT**" in table and "needs_review" in table


def test_recommendations_must_cover_exactly_the_priority_rows(small_review):
    keys = [r.key for r in rv.priority_rows(small_review)]
    ok = {k: v for k, v in recs().items() if k in keys}
    rv.validate_recommendations(small_review, ok)
    with pytest.raises(rv.RecommendationError, match="no recommendation for"):
        rv.validate_recommendations(small_review, {k: v for k, v in ok.items() if k != keys[0]})
    with pytest.raises(rv.RecommendationError, match="not a priority row"):
        rv.validate_recommendations(small_review, {**ok, "RU00:none:none": {"key": "RU00:none:none", "action": "REMOVE", "reason": "x"}})


def test_an_action_must_fit_the_rows_current_level(small_review):
    keys = [r.key for r in rv.priority_rows(small_review)]
    related = next(k for k in keys if rep(small_review, k).mapping.relevance_level == "related")
    direct = next(k for k in keys if rep(small_review, k).mapping.relevance_level == "direct")
    base = {k: {"key": k, "action": "NEEDS MORE SOURCE REVIEW", "reason": "x"} for k in keys}
    for action, bad_key in [("APPROVE DIRECT", related), ("DOWNGRADE TO RELATED", related), ("SPLIT RANGE", related), ("KEEP RELATED", direct)]:
        with pytest.raises(rv.RecommendationError, match="only applies to"):
            rv.validate_recommendations(small_review, {**base, bad_key: {"key": bad_key, "action": action, "reason": "x"}})


def test_the_recommendation_file_format_is_validated(tmp_path):
    def write(items):
        p = tmp_path / "r.json"
        p.write_text(json.dumps(items))
        return p

    assert rv.load_recommendations(write([{"key": "a", "action": "REMOVE", "reason": "x"}]))["a"]["action"] == "REMOVE"
    for bad, why in [("x", "JSON list"), ([{"key": "a", "action": "MAYBE", "reason": "x"}], "action must be"), ([{"key": "a", "action": "REMOVE"}], "key and reason"),
                     ([{"key": "a", "action": "REMOVE", "reason": "x"}, {"key": "a", "action": "REMOVE", "reason": "y"}], "duplicate")]:
        with pytest.raises(rv.RecommendationError, match=why):
            rv.load_recommendations(write(bad))
    with pytest.raises(rv.RecommendationError, match="cannot read"):
        rv.load_recommendations(tmp_path / "missing.json")


def test_clause_wording_quotes_the_cited_clauses_and_marks_inferred_scope():
    from poltracker.committee_industry import Mapping

    base = dict(id=1, chamber="house", committee_code="AS00", subcommittee_code=None, committee_name="Armed Services", subcommittee_name=None, sic_start=3720, sic_end=3729,
                industry_pattern=None, relevance_level="direct", rationale="Aircraft (Rule X 1(c)(4)).", jurisdiction_text="(2) Common defense generally. (4) The Department of Defense generally. (9) Shipbuilding.",
                source_citation="Rule X, clause 1(c)", source_url="https://x", reviewed_at=None, mapping_version="v", jurisdiction_basis="rule_x_text")
    assert rv.clause_wording(Mapping(**base)) == "(4) The Department of Defense generally."
    cited_in_citation = rv.clause_wording(Mapping(**{**base, "rationale": "Seapower.", "source_citation": "Rule X, clause 1(c)(9); subcommittee name", "jurisdiction_basis": "subcommittee_name"}))
    assert cited_in_citation.startswith("(9) Shipbuilding.") and "inferred from its name" in cited_in_citation
    assert rv.clause_wording(Mapping(**{**base, "rationale": "x", "source_citation": None, "jurisdiction_basis": "committee_name"})).startswith("(2) Common defense")  # no clause cited: opening excerpt


def test_generating_the_table_leaves_every_mapping_unchanged(universe, tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(ROWS))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    review_ = rv.build_review(universe, load_rows(path), SIC)
    keys = [r.key for r in rv.priority_rows(review_)]
    rv.render_priority_table(review_, {k: {"key": k, "action": "NEEDS MORE SOURCE REVIEW", "reason": "x"} for k in keys})
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


# --- the shipped recommendations ---------------------------------------------------------------------------------

REC_FILE = ROOT / "docs" / "review" / "round1" / "priority_recommendations_2026.1-draft.json"


def test_the_archived_round_1_recommendations_are_well_formed():
    # An archive of the pre-decision proposals: some of its rows were since split, downgraded or removed, so only its format is checked.
    recs_ = rv.load_recommendations(REC_FILE)
    assert len(recs_) == 50
    assert all(rec["action"] in rv.ACTIONS and rec["reason"].strip() for rec in recs_.values())


# --- the round 1 review decisions, as applied to the shipped file -------------------------------------------------

def shipped():
    return {rv.row_key(m): r for m, r in zip(rv.to_mappings(load_rows(REAL)), load_rows(REAL))}


def test_round_1_approved_rows_are_reviewed_direct_and_the_aircraft_row_keeps_its_civil_military_note():
    rows = shipped()
    for key in ["BA00:6000-6099:direct", "BA00/BA16:6200-6299:direct", "IF00:4800-4899:direct", "IF00/IF03:4911-4939:direct", "II00:1000-1099:direct"]:
        assert rows[key]["review_status"] == "reviewed" and rows[key]["relevance_level"] == "direct"
    assert "civilian and military aviation" in rows["AS00:3720-3729:direct"]["review_note"]


def test_round_1_splits_separate_the_mixed_pieces_and_cover_the_original_range_exactly():
    rows = shipped()
    for committee in ("BA00", "BA00/BA04"):
        assert rows[f"{committee}:6300-6319:direct"]["review_status"] == "reviewed"
        assert rows[f"{committee}:6320-6329:related"]["review_status"] == "reviewed"  # health plans are not a blanket direct match
        assert rows[f"{committee}:6330-6499:direct"]["review_status"] == "reviewed"
        assert f"{committee}:6300-6499:direct" not in rows
    assert "BA00:6199-6199:related" in rows and "BA00:6100-6198:direct" in rows
    assert "PW00:1623-1629:related" in rows and "PW00:1600-1622:direct" in rows
    assert "AG00/AG16:2060-2069:related" in rows and "AG00/AG16:2070-2079:direct" in rows
    for r in rows.values():
        if r["review_note"] and "Split from" in r["review_note"]:
            assert r["rationale"].rstrip().endswith(".") and f"Official SIC titles in {r['sic_start']}-{r['sic_end']}:" in r["rationale"]


def test_round_1_downgrades_and_removals():
    rows = shipped()
    for key in ["PW00:4730-4739:related", "AG00/AG03:2000-2079:related", "BA00/BA04:6500-6599:related", "VR00/VR03:8050-8099:related",
                "PW00/PW02:1623-1623:related", "PW00/PW02:4941-4941:related"]:
        assert rows[key]["review_status"] == "reviewed", key
    assert not any(k.startswith(("SY00:8731", "SY00/SY15:8731")) for k in rows)  # clinical-research-contractor mapping removed consistently


def test_round_1_rows_needing_more_source_review_stay_needs_review_with_a_note():
    rows = shipped()
    for key in ["WM00/WM02:8000-8099:direct", "AG00/AG22:6221-6221:direct", "IF00/IF16:7370-7373:related", "JU00/JU03:7370-7373:related"]:
        assert rows[key]["review_status"] == "needs_review" and rows[key]["review_note"].startswith("Needs more source review")
    assert rows["AG00/AG03:2090-2099:direct"]["review_status"] == "needs_review"  # not named in the decisions: left alone


def test_review_category_only_credits_reviewed_direct_matches():
    from types import SimpleNamespace as NS

    from poltracker.committee_industry_report import review_category

    def rel(status, *matches):
        return NS(status=status, matches=[NS(level=lv, review_status=rs) for lv, rs in matches])

    assert review_category(rel("relevant", ("direct", "reviewed"), ("direct", "needs_review"))) == "reviewed_direct"
    assert review_category(rel("relevant", ("related", "reviewed"), ("direct", "needs_review"))) == "reviewed_related_only"  # needs_review never lifts it
    assert review_category(rel("relevant", ("direct", "needs_review"))) == "needs_review_only"
    assert review_category(rel("not_relevant")) == "no_relevance" and review_category(rel("unknown")) == "unknown"
