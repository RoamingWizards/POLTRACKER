"""Reviewed overrides: explicit, validated, provenance-keeping, and only for records the matcher left unmatched."""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from poltracker.enrich_politicians import enrich_politicians
from poltracker.models import Politician, PoliticianAliasOverride
from poltracker.politician_overrides import OverrideError, add_override, load_overrides_file

from test_enrich_politicians import NOW, FakeProvider, official

REVIEWED = datetime(2026, 10, 7)
REASON = "Dan is the standard short form of Daniel; sole Crenshaw in the House"
SOURCE = "https://api.congress.gov/v3/member/C001120"

ROSTER = [
    official("C001120", "Dan", "Crenshaw"),
    official("D000399", "Lloyd", "Doggett"),
    official("S000001", "Greg", "Smith", "senate", "OH"),
    official("J000299", "Mike", "Johnson", state="LA"),
    official("J000999", "Mike", "Johnson", state="OH"),
]


@pytest.fixture
def pols(session_factory):
    with session_factory() as s:
        rows = [
            Politician(canonical_key="house:danielcrenshaw", name="Daniel Crenshaw", chamber="house"),
            Politician(canonical_key="house:lloyddoggett", name="Lloyd Doggett", chamber="house"),
            Politician(canonical_key="house:gregsmith", name="Greg Smith", chamber="house", state="TX"),
            Politician(canonical_key="house:mikejohnson", name="Mike Johnson", chamber="house"),
        ]
        s.add_all(rows)
        s.commit()
        return {p.name: p.id for p in rows}


def run(sf, roster=ROSTER, **kw):
    return enrich_politicians(sf, FakeProvider(roster), now=kw.pop("now", NOW), **kw)


def record(sf, pid, bioguide="C001120", reason=REASON, source=SOURCE):
    with sf() as s:
        add_override(s, pid, bioguide, reason, source, REVIEWED)
        s.commit()


def get(sf, pid):
    with sf() as s:
        return s.get(Politician, pid)


def test_the_matcher_alone_still_rejects_the_nickname(session_factory, pols):
    report = run(session_factory)
    p = get(session_factory, pols["Daniel Crenshaw"])
    assert p.bioguide_id is None and p.enrichment_status == "unmatched" and not report.overrides_applied


def test_a_valid_override_resolves_an_unmatched_politician_and_keeps_provenance(session_factory, pols):
    pid = pols["Daniel Crenshaw"]
    run(session_factory)  # unmatched first, as in real use
    record(session_factory, pid)
    report = run(session_factory, now=NOW + timedelta(hours=1))  # applied on the next run, no waiting period
    p = get(session_factory, pid)
    assert (p.bioguide_id, p.enrichment_status, p.enrichment_method, p.party, p.state) == ("C001120", "matched", "override", "D", "TX")
    assert REASON in p.enrichment_note and SOURCE in p.enrichment_note and "2026-10-07" in p.enrichment_note
    assert report.overrides_applied == [(pid, "Daniel Crenshaw", "C001120")]
    with session_factory() as s:
        row = s.scalar(select(PoliticianAliasOverride))
    assert (row.politician_id, row.bioguide_id, row.reason, row.source, row.reviewed_at) == (pid, "C001120", REASON, SOURCE, REVIEWED)


def test_automatic_matches_are_labelled_as_such_and_never_use_overrides(session_factory, pols):
    record(session_factory, pols["Daniel Crenshaw"])
    run(session_factory)
    doggett = get(session_factory, pols["Lloyd Doggett"])
    assert doggett.enrichment_method == "exact_name+chamber" and doggett.enrichment_note is None


def test_an_override_cannot_replace_an_automatic_match(session_factory, pols):
    with pytest.raises(OverrideError, match="already matched automatically"):
        run(session_factory)
        with session_factory() as s:
            add_override(s, pols["Lloyd Doggett"], "C001120", REASON, SOURCE, REVIEWED)


def test_an_override_for_a_record_that_later_matches_automatically_is_ignored_with_a_warning(session_factory, pols):
    pid = pols["Daniel Crenshaw"]
    record(session_factory, pid, "D000399")  # a (bad) override recorded while unmatched
    roster = ROSTER + [official("C009999", "Daniel", "Crenshaw")]  # now the plain name exists officially
    report = run(session_factory, roster=roster)
    assert get(session_factory, pid).bioguide_id == "C009999"
    assert any("override D000399 ignored" in w for w in report.warnings)


def test_an_override_does_not_resolve_an_ambiguous_record(session_factory, pols):
    pid = pols["Mike Johnson"]
    record(session_factory, pid, "J000299")
    run(session_factory)
    p = get(session_factory, pid)
    assert p.bioguide_id is None and p.enrichment_status == "ambiguous"


def test_an_unknown_bioguide_id_fails_safely_at_apply_time(session_factory, pols):
    pid = pols["Daniel Crenshaw"]
    record(session_factory, pid, "Z999999")
    report = run(session_factory)
    p = get(session_factory, pid)
    assert p.bioguide_id is None and p.enrichment_status == "conflict" and "not in the official roster" in p.enrichment_note
    assert [u.status for u in report.unresolved if u.politician_id == pid] == ["conflict"]


def test_a_malformed_bioguide_id_is_rejected_when_recorded(session_factory, pols):
    for bad in ("", "c001120x", "12345", "C00112"):
        with session_factory() as s, pytest.raises(OverrideError, match="not a Bioguide ID"):
            add_override(s, pols["Daniel Crenshaw"], bad, REASON, SOURCE)


def test_a_missing_reason_or_source_or_politician_is_rejected(session_factory, pols):
    with session_factory() as s:
        with pytest.raises(OverrideError, match="reason is required"):
            add_override(s, pols["Daniel Crenshaw"], "C001120", " ", SOURCE)
        with pytest.raises(OverrideError, match="source is required"):
            add_override(s, pols["Daniel Crenshaw"], "C001120", REASON, "")
        with pytest.raises(OverrideError, match="does not exist"):
            add_override(s, 9999, "C001120", REASON, SOURCE)


def test_wrong_chamber_is_rejected_at_apply_time(session_factory, pols):
    pid = pols["Daniel Crenshaw"]
    record(session_factory, pid, "S000001")  # a Senate member for a House politician
    run(session_factory)
    p = get(session_factory, pid)
    assert p.bioguide_id is None and p.enrichment_status == "conflict" and "senate member" in p.enrichment_note


def test_wrong_state_is_rejected_at_apply_time(session_factory, pols):
    pid = pols["Greg Smith"]  # recorded as TX
    with session_factory() as s:
        s.add(Politician(canonical_key="house:x", name="Unused", chamber="house"))  # noqa: keep ids stable
        s.commit()
    roster = ROSTER + [official("S000002", "Gregory", "Smith", "house", "OH")]
    record(session_factory, pid, "S000002")
    run(session_factory, roster=roster)
    p = get(session_factory, pid)
    assert p.bioguide_id is None and p.enrichment_status == "conflict" and "recorded as TX" in p.enrichment_note


def test_an_id_already_assigned_to_another_politician_cannot_be_recorded_or_applied(session_factory, pols):
    run(session_factory)  # Doggett now owns D000399
    with session_factory() as s, pytest.raises(OverrideError, match="already assigned to politician"):
        add_override(s, pols["Daniel Crenshaw"], "D000399", REASON, SOURCE)
    # ...and if it slipped into the table anyway (say, assigned later), applying it is still refused
    with session_factory() as s:
        s.add(PoliticianAliasOverride(politician_id=pols["Daniel Crenshaw"], bioguide_id="D000399", reason="x", source="y", reviewed_at=REVIEWED))
        s.commit()
    run(session_factory, now=NOW + timedelta(hours=1))
    p = get(session_factory, pols["Daniel Crenshaw"])
    assert p.bioguide_id is None and p.enrichment_status == "conflict" and "not merged" in p.enrichment_note
    with session_factory() as s:
        assert len(s.scalars(select(Politician).where(Politician.bioguide_id == "D000399")).all()) == 1


def test_one_id_cannot_be_the_override_for_two_politicians(session_factory, pols):
    record(session_factory, pols["Daniel Crenshaw"])
    with session_factory() as s, pytest.raises(OverrideError, match="already the override for politician"):
        add_override(s, pols["Greg Smith"], "C001120", REASON, SOURCE)


def test_re_enrichment_with_an_override_is_idempotent(session_factory, pols):
    record(session_factory, pols["Daniel Crenshaw"])
    run(session_factory)

    def state():
        with session_factory() as s:
            return [(p.id, p.bioguide_id, p.party, p.state, p.district, p.enrichment_status, p.enrichment_method, p.enrichment_note)
                    for p in s.scalars(select(Politician).order_by(Politician.id))]

    first = state()
    again = FakeProvider(ROSTER)
    assert enrich_politicians(session_factory, again, now=NOW + timedelta(days=1)).status == "nothing_to_do" and again.calls == 0
    run(session_factory, now=NOW + timedelta(days=2), force=True)
    assert state() == first


def test_a_dry_run_applies_nothing(session_factory, pols):
    record(session_factory, pols["Daniel Crenshaw"])
    report = run(session_factory, dry_run=True)
    assert report.overrides_applied and get(session_factory, pols["Daniel Crenshaw"]).bioguide_id is None


def test_the_overrides_file_is_all_or_nothing_and_reloading_is_idempotent(session_factory, pols, tmp_path):
    good = {"politician_id": pols["Daniel Crenshaw"], "bioguide_id": "C001120", "reason": REASON, "source": SOURCE, "reviewed_at": "2026-10-07"}
    bad = {"politician_id": pols["Greg Smith"], "bioguide_id": "nope", "reason": REASON, "source": SOURCE, "reviewed_at": "2026-10-07"}
    path = tmp_path / "o.json"
    path.write_text(json.dumps([good, bad]))
    with session_factory() as s:
        with pytest.raises(OverrideError, match="entry 2"):
            load_overrides_file(s, path)
        s.rollback()
    with session_factory() as s:
        assert s.scalars(select(PoliticianAliasOverride)).all() == []  # the valid first entry was not kept
    path.write_text(json.dumps([good]))
    for _ in range(2):  # loading the same reviewed file twice changes nothing
        with session_factory() as s:
            load_overrides_file(s, path)
            s.commit()
    run(session_factory)
    with session_factory() as s:
        assert len(s.scalars(select(PoliticianAliasOverride)).all()) == 1
    with session_factory() as s:  # and still loadable after the override has been applied
        load_overrides_file(s, path)


def test_an_unreadable_or_non_list_file_is_rejected(session_factory, tmp_path):
    with session_factory() as s:
        with pytest.raises(OverrideError, match="cannot read"):
            load_overrides_file(s, tmp_path / "missing.json")
        (tmp_path / "o.json").write_text('{"a": 1}')
        with pytest.raises(OverrideError, match="JSON list"):
            load_overrides_file(s, tmp_path / "o.json")
