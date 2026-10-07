"""The enrichment service writes only verified matches, never calls providers needlessly, and never crashes the app."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from poltracker.enrich_politicians import enrich_politicians
from poltracker.models import CommitteeAssignment, Politician, Trade
from poltracker.providers.base import ProviderError
from poltracker.providers.politicians import CommitteeProvider, CommitteeSeat, NotConfigured, OfficialMember, PoliticianProvider

NOW = datetime(2026, 10, 7, 12, 0)


def official(bio, first, last, chamber="house", state="TX", **kw):
    return OfficialMember(bio, first, last, chamber, state=state, party="D", district="1", active=True,
                          official_url=f"https://www.congress.gov/member/x/{bio}", term_start_year=2025,
                          full_name=f"{first} {last}", source="fake.gov", **kw)


class FakeProvider(PoliticianProvider):
    name = "fake.gov"

    def __init__(self, members=(), error=None):
        self.members, self.error, self.calls = list(members), error, 0

    @property
    def requests_made(self):
        return self.calls

    def list_members(self, *, chamber=None):
        self.calls += 1
        if self.error:
            raise self.error
        return self.members

    def get_member(self, bioguide_id):
        return next((m for m in self.members if m.bioguide_id == bioguide_id), None)


class FakeCommittees(CommitteeProvider):
    name, chambers = "fake.committees", ("house",)

    def __init__(self, seats=None, error=None):
        self.seats, self.error, self.calls = seats or {}, error, 0

    def get_committees(self, bioguide_ids=None):
        self.calls += 1
        if self.error:
            raise self.error
        return {k: v for k, v in self.seats.items() if bioguide_ids is None or k in bioguide_ids}


def seat(bio, code="AG00", sub="", role="Member"):
    return CommitteeSeat(bio, "Committee on Agriculture", code, "house", "Nutrition" if sub else None, sub, role, source="fake.committees")


@pytest.fixture
def pols(session_factory):
    with session_factory() as s:
        rows = [
            Politician(canonical_key="house:lloyddoggett", name="Lloyd Doggett", chamber="house"),
            Politician(canonical_key="house:danielcrenshaw", name="Dan Crenshaw", chamber="house"),
            Politician(canonical_key="house:mikejohnson", name="Mike Johnson", chamber="house"),
            Politician(canonical_key="senate:ronwyden", name="Ron Wyden", chamber="senate", state="OR"),
        ]
        s.add_all(rows)
        s.commit()
        return {p.name: p.id for p in rows}


ROSTER = [
    official("D000399", "Lloyd", "Doggett"),
    official("C001120", "Daniel", "Crenshaw"),
    official("J000299", "Mike", "Johnson", state="LA"),
    official("J000999", "Mike", "Johnson", state="OH"),
]


def get(session_factory, pid):
    with session_factory() as s:
        return s.get(Politician, pid)


def test_a_verified_match_writes_official_fields_and_nothing_else_changes(session_factory, pols):
    with session_factory() as s:
        before = s.scalar(select(func.count(Trade.id)))
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    p = get(session_factory, pols["Lloyd Doggett"])
    assert (p.bioguide_id, p.party, p.state, p.district, p.active, p.enrichment_status, p.enrichment_source) == (
        "D000399", "D", "TX", "1", True, "matched", "fake.gov")
    assert p.official_url.endswith("D000399") and p.enriched_at == NOW and p.term_start_year == 2025
    assert p.id == pols["Lloyd Doggett"]  # ids are preserved
    assert report.status == "ok" and [m[2] for m in report.matched] == ["D000399"]


def test_unmatched_and_ambiguous_politicians_get_no_identifier_but_a_recorded_reason(session_factory, pols):
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    crenshaw = get(session_factory, pols["Dan Crenshaw"])
    assert crenshaw.bioguide_id is None and crenshaw.enrichment_status == "unmatched"
    assert "Daniel Crenshaw" in crenshaw.enrichment_note
    johnson = get(session_factory, pols["Mike Johnson"])
    assert johnson.bioguide_id is None and johnson.enrichment_status == "ambiguous" and "J000999" in johnson.enrichment_note
    assert johnson.party is None and johnson.state is None  # nothing taken from a candidate
    wyden = get(session_factory, pols["Ron Wyden"])
    assert wyden.enrichment_status == "unmatched" and wyden.state == "OR"
    assert {u.status for u in report.unresolved} == {"unmatched", "ambiguous"} and len(report.unresolved) == 3


def test_a_missing_key_reports_not_configured_and_changes_nothing(session_factory, pols):
    report = enrich_politicians(session_factory, FakeProvider(error=NotConfigured("CONGRESS_API_KEY is not set")), now=NOW)
    assert report.status == "not_configured" and "CONGRESS_API_KEY" in report.message
    assert all(get(session_factory, pid).enrichment_checked_at is None for pid in pols.values())


def test_a_provider_outage_reports_the_error_and_leaves_politicians_retryable(session_factory, pols):
    report = enrich_politicians(session_factory, FakeProvider(error=ProviderError("HTTP 503")), now=NOW)
    assert report.status == "provider_error" and "503" in report.message
    assert all(get(session_factory, pid).enrichment_status is None for pid in pols.values())
    retry = enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)  # no waiting period after an outage
    assert len(retry.matched) == 1


def test_current_records_cause_no_provider_call_at_all(session_factory, pols):
    enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    again = FakeProvider(ROSTER)
    report = enrich_politicians(session_factory, again, now=NOW + timedelta(days=1))
    assert again.calls == 0 and report.status == "nothing_to_do"
    assert report.skipped_current == 1 and report.skipped_recent_attempt == 3


def test_unmatched_politicians_are_retried_after_the_retry_window_and_matched_ones_after_the_stale_window(session_factory, pols):
    enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    retry = FakeProvider(ROSTER + [official("W000779", "Ron", "Wyden", "senate", "OR")])
    report = enrich_politicians(session_factory, retry, now=NOW + timedelta(days=8))
    assert retry.calls == 1 and report.skipped_current == 1 and len(report.matched) == 1  # Wyden is now on the roster
    assert get(session_factory, pols["Ron Wyden"]).bioguide_id == "W000779"
    stale = FakeProvider(ROSTER)
    enrich_politicians(session_factory, stale, now=NOW + timedelta(days=31))
    assert stale.calls == 1


def test_force_ignores_the_recency_rules(session_factory, pols):
    enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    forced = FakeProvider(ROSTER)
    assert enrich_politicians(session_factory, forced, now=NOW, force=True).considered == 4 and forced.calls == 1


def test_limit_and_ids_restrict_the_work(session_factory, pols):
    assert enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW, limit=1).considered == 1
    only = enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW, only_ids={pols["Ron Wyden"]}, force=True)
    assert only.considered == 1


def test_a_dry_run_reports_matches_but_writes_nothing(session_factory, pols):
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), FakeCommittees({"D000399": [seat("D000399")]}), now=NOW, dry_run=True)
    assert len(report.matched) == 1 and report.committee_seats == 1 and report.dry_run
    p = get(session_factory, pols["Lloyd Doggett"])
    assert p.bioguide_id is None and p.enrichment_checked_at is None
    with session_factory() as s:
        assert s.scalar(select(func.count(CommitteeAssignment.id))) == 0


def test_an_official_already_linked_to_another_record_is_not_merged_or_duplicated(session_factory, pols):
    with session_factory() as s:
        s.add(Politician(canonical_key="house:lloydjdoggett", name="Lloyd J Doggett", chamber="house"))
        s.commit()
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    with session_factory() as s:
        linked = s.scalars(select(Politician).where(Politician.bioguide_id == "D000399")).all()
        dup = s.scalar(select(Politician).where(Politician.name == "Lloyd J Doggett"))
    assert len(linked) == 1 and dup.enrichment_status == "conflict" and "not merged" in dup.enrichment_note
    assert any(u.status == "conflict" for u in report.unresolved)


def test_an_existing_different_identifier_is_never_overwritten(session_factory, pols):
    with session_factory() as s:
        s.get(Politician, pols["Lloyd Doggett"]).bioguide_id = "X999999"
        s.commit()
    enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    p = get(session_factory, pols["Lloyd Doggett"])
    assert p.bioguide_id == "X999999" and p.enrichment_status == "conflict"


def test_a_failed_later_attempt_does_not_downgrade_a_verified_match(session_factory, pols):
    enrich_politicians(session_factory, FakeProvider(ROSTER), now=NOW)
    enrich_politicians(session_factory, FakeProvider([]), now=NOW + timedelta(days=40))  # roster no longer lists him
    p = get(session_factory, pols["Lloyd Doggett"])
    assert p.bioguide_id == "D000399" and p.enrichment_status == "matched"


def test_committee_seats_are_stored_and_replaced_on_refresh(session_factory, pols):
    first = FakeCommittees({"D000399": [seat("D000399"), seat("D000399", sub="AG03", role="Vice Chair")]})
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), first, now=NOW)
    assert report.committee_seats == 2
    with session_factory() as s:
        rows = s.scalars(select(CommitteeAssignment).order_by(CommitteeAssignment.id)).all()
    assert [(r.committee_code, r.subcommittee_code, r.role) for r in rows] == [("AG00", "", "Member"), ("AG00", "AG03", "Vice Chair")]
    assert all(r.politician_id == pols["Lloyd Doggett"] and r.source == "fake.committees" for r in rows)
    enrich_politicians(session_factory, FakeProvider(ROSTER), FakeCommittees({"D000399": [seat("D000399", "BA00")]}), now=NOW, force=True)
    with session_factory() as s:
        assert [r.committee_code for r in s.scalars(select(CommitteeAssignment))] == ["BA00"]  # replaced, not appended


def test_a_committee_outage_keeps_the_existing_seats_and_still_enriches(session_factory, pols):
    enrich_politicians(session_factory, FakeProvider(ROSTER), FakeCommittees({"D000399": [seat("D000399")]}), now=NOW)
    report = enrich_politicians(session_factory, FakeProvider(ROSTER), FakeCommittees(error=ProviderError("HTTP 403")), now=NOW, force=True)
    assert "unavailable" in report.committee_message and report.status == "ok"
    with session_factory() as s:
        assert s.scalar(select(func.count(CommitteeAssignment.id))) == 1


def test_senators_get_no_committee_lookup_from_a_house_only_source(session_factory, pols):
    committees = FakeCommittees()
    roster = [official("W000779", "Ron", "Wyden", "senate", "OR")]
    enrich_politicians(session_factory, FakeProvider(roster), committees, now=NOW, only_ids={pols["Ron Wyden"]})
    assert committees.calls == 0
