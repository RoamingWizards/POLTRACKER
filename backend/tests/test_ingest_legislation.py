"""Legislative ingestion: scope, idempotency, duplicate prevention, politician linking and dry runs, with a fake provider."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from poltracker.ingest_legislation import default_window, ingest_legislation
from poltracker.models import (
    BillAction, Hearing, HearingCommittee, Legislation, LegislationCommittee, LegislationSubject, Politician, PoliticianLegislation, PriceBar, Security, Trade,
)
from poltracker.providers import legislation as leg
from poltracker.providers.base import ProviderError, ProviderRateLimited
from poltracker.providers.politicians import NotConfigured

FROM, TO, TODAY = date(2025, 1, 3), date(2026, 10, 7), date(2026, 10, 7)
OLD = date(2026, 9, 1)  # an updateDate safely before "today", so unchanged-skipping applies


@dataclass
class B:
    number: int
    latest: date = date(2026, 5, 10)
    update: date = OLD
    actions: list = field(default_factory=lambda: [leg.BillAction(date(2026, 5, 10), "Referred to committee", "H11100", "IntroReferral")])
    subjects: list = field(default_factory=lambda: ["Health"])
    policy: str | None = "Health"
    summaries: list = field(default_factory=list)
    cosponsors: list = field(default_factory=list)
    committees: list = field(default_factory=lambda: [leg.CommitteeRef("hsif00", "Energy and Commerce Committee", "House")])
    sponsor: leg.BillSponsor | None = field(default_factory=lambda: leg.BillSponsor("D000399", "Rep. Doggett, Lloyd [D-TX-37]", "D", "TX"))
    title: str = "A bill"
    introduced: date = date(2026, 5, 10)
    congress: int = 119
    bill_type: str = "hr"

    @property
    def ref(self):
        return leg.BillRef(self.congress, self.bill_type, self.number, self.title, self.update, self.latest, "latest action text")


class Fake(leg.LegislationProvider):
    def __init__(self, bills=(), hearings=(), bad=(), rate_limit_at=None, error=None):
        self.bills, self.hearings, self.bad, self.rate_limit_at, self.error = list(bills), list(hearings), set(bad), rate_limit_at, error
        self.requests_made, self.detail_calls = 0, 0

    def _hit(self):
        self.requests_made += 1
        if self.error:
            raise self.error

    def list_bills(self, congress, *, from_date=None, limit=None):
        self._hit()
        for b in sorted(self.bills, key=lambda b: b.update, reverse=True):
            if b.congress == congress and (from_date is None or b.update >= from_date):
                yield b.ref

    def _bill(self, ref):
        self.detail_calls += 1
        self.requests_made += 1
        if ref.number in self.bad:
            raise ProviderError("HTTP 500")
        if self.rate_limit_at is not None and self.detail_calls >= self.rate_limit_at:
            raise ProviderRateLimited("429")
        return next(b for b in self.bills if b.number == ref.number and b.congress == ref.congress)

    def get_bill(self, ref):
        b = self._bill(ref)
        return leg.Bill(b.ref, "House", b.introduced, b.policy, b.sponsor, leg.bill_public_url(*b.ref.key), len(b.subjects), len(b.summaries), len(b.cosponsors), len(b.committees), len(b.actions))

    def get_bill_actions(self, ref):
        self.requests_made += 1
        if ref.number in self.bad:
            raise ProviderError("HTTP 500")
        return next(b for b in self.bills if b.number == ref.number).actions

    def get_bill_subjects(self, ref):
        self.requests_made += 1
        b = next(b for b in self.bills if b.number == ref.number)
        return b.policy, b.subjects

    def get_bill_summaries(self, ref):
        self.requests_made += 1
        return next(b for b in self.bills if b.number == ref.number).summaries

    def get_bill_cosponsors(self, ref):
        self.requests_made += 1
        return next(b for b in self.bills if b.number == ref.number).cosponsors

    def get_bill_committees(self, ref):
        self.requests_made += 1
        return next(b for b in self.bills if b.number == ref.number).committees

    def list_hearings(self, congress, *, limit=None):
        self._hit()
        return iter([h.ref for h in self.hearings if h.ref.congress == congress])

    def get_hearing(self, ref):
        self.requests_made += 1
        return next(h for h in self.hearings if h.ref == ref)


def hearing(jacket, *dates, committees=(), chamber="house", update=datetime(2026, 9, 1)):
    return leg.Hearing(leg.HearingRef(119, chamber, jacket, update), f"Hearing {jacket}", f"CIT-{jacket}", tuple(dates), tuple(committees), None,
                       f"https://api.congress.gov/v3/hearing/119/{chamber}/{jacket}")


@pytest.fixture
def pols(session_factory):
    with session_factory() as s:
        a = Politician(canonical_key="house:a", name="Lloyd Doggett", chamber="house", bioguide_id="D000399")
        b = Politician(canonical_key="senate:b", name="Pat Senator", chamber="senate", bioguide_id="S000001")
        c = Politician(canonical_key="house:c", name="Jane Roe", chamber="house")  # no Bioguide ID
        s.add_all([a, b, c])
        s.flush()
        sec = Security(ticker="XYZ")
        s.add(sec)
        s.flush()
        s.add(Trade(source="t", fingerprint="f1", politician_id=a.id, security_id=sec.id, politician_name="Lloyd Doggett", chamber="house", ticker="XYZ",
                    transaction_type="buy", transaction_date=date(2026, 5, 1), disclosure_date=date(2026, 5, 20)))
        s.add(PriceBar(security_id=sec.id, date=date(2026, 5, 1), close=1.0, adj_close=1.0, provider="t"))
        s.commit()
        return {"a": a.id, "b": b.id, "c": c.id}


def run(sf, provider, **kw):
    kw.setdefault("from_date", FROM)
    kw.setdefault("to_date", TO)
    kw.setdefault("today", TODAY)
    return ingest_legislation(sf, provider, **kw)


def count(sf, model):
    with sf() as s:
        return s.scalar(select(func.count()).select_from(model))


def dump(sf):
    """Every legislative table, for before/after comparisons (ids and timestamps excluded)."""
    out = {}
    with sf() as s:
        out["leg"] = sorted(s.execute(text("select congress,bill_type,bill_number,title,summary,policy_area,sponsor_bioguide_id,cosponsor_count,api_update_date,latest_action_date from legislation")).all())
        out["subjects"] = sorted(s.execute(text("select l.bill_number, x.subject from legislation_subjects x join legislation l on l.id=x.legislation_id")).all())
        out["committees"] = sorted(s.execute(text("select l.bill_number, x.committee_code from legislation_committees x join legislation l on l.id=x.legislation_id")).all())
        out["actions"] = sorted(s.execute(text("select l.bill_number, x.action_date, x.action_key from bill_actions x join legislation l on l.id=x.legislation_id")).all())
        out["links"] = sorted(s.execute(text("select politician_id, relationship, legislation_id from politician_legislation")).all())
        out["hearings"] = sorted(s.execute(text("select jacket_number, hearing_date, title from hearings")).all())
    return out


# --- what gets stored -----------------------------------------------------------------------------------------

def test_a_bill_is_stored_with_its_official_identity_children_and_provenance(session_factory, pols):
    cos = [leg.BillCosponsor("S000001", "Sen. Pat", date(2026, 5, 11), True, None)]
    summ = [leg.BillSummary(date(2026, 5, 10), "Introduced", "Plain summary text.", "00", datetime(2026, 5, 11))]
    b = B(100, cosponsors=cos, summaries=summ, subjects=["Health", "Taxation"])
    r = run(session_factory, Fake([b]))
    assert (r.status, r.bills_fetched, r.bills_inserted, r.subjects_inserted, r.committees_inserted, r.actions_inserted, r.links_inserted) == ("ok", 1, 1, 2, 1, 1, 2)
    with session_factory() as s:
        row = s.scalar(select(Legislation))
        assert (row.congress, row.bill_type, row.bill_number, row.title, row.policy_area) == (119, "hr", 100, "A bill", "Health")
        assert row.source_url == "https://www.congress.gov/bill/119th-congress/house-bill/100" and row.api_update_date == OLD
        assert (row.sponsor_bioguide_id, row.sponsor_name, row.cosponsor_count, row.summary, row.summary_date) == ("D000399", "Rep. Doggett, Lloyd [D-TX-37]", 1, "Plain summary text.", date(2026, 5, 10))
        assert {x.subject for x in row.subjects} == {"Health", "Taxation"}
        assert [(c.committee_code, c.committee_name, c.chamber) for c in row.committees] == [("hsif00", "Energy and Commerce Committee", "House")]
        assert [(a.action_date, a.action_text, a.action_code) for a in row.actions] == [(date(2026, 5, 10), "Referred to committee", "H11100")]


def test_the_most_recent_summary_wins(session_factory, pols):
    old = leg.BillSummary(date(2026, 1, 1), "a", "old text", "00", datetime(2026, 1, 2))
    new = leg.BillSummary(date(2026, 3, 1), "b", "new text", "01", datetime(2026, 3, 2))
    run(session_factory, Fake([B(1, summaries=[new, old])]))
    with session_factory() as s:
        assert s.scalar(select(Legislation.summary)) == "new text"


def test_a_bill_without_subjects_summary_or_committees_is_still_stored(session_factory, pols):
    r = run(session_factory, Fake([B(1, subjects=[], policy=None, committees=[], summaries=[], sponsor=None)]))
    assert r.bills_inserted == 1 and count(session_factory, LegislationSubject) == 0 and count(session_factory, LegislationCommittee) == 0
    with session_factory() as s:
        row = s.scalar(select(Legislation))
        assert (row.summary, row.policy_area, row.sponsor_bioguide_id) == (None, None, None)


# --- identity and duplicates ----------------------------------------------------------------------------------

def test_bill_identity_is_the_official_triple_and_the_database_enforces_it(session_factory, pols):
    run(session_factory, Fake([B(5)]))
    with session_factory() as s:
        s.add(Legislation(congress=119, bill_type="hr", bill_number=5, title="a different title"))
        with pytest.raises(IntegrityError):
            s.commit()
    with session_factory() as s:  # same number in another type or another Congress is a different bill
        s.add_all([Legislation(congress=119, bill_type="s", bill_number=5), Legislation(congress=118, bill_type="hr", bill_number=5)])
        s.commit()


def test_a_changed_title_updates_the_same_bill_instead_of_creating_another(session_factory, pols):
    run(session_factory, Fake([B(5, title="Old title")]))
    r = run(session_factory, Fake([B(5, title="New title", update=TODAY - timedelta(days=1))]))
    assert (r.bills_inserted, r.bills_updated) == (0, 1) and count(session_factory, Legislation) == 1
    with session_factory() as s:
        assert s.scalar(select(Legislation.title)) == "New title"


def test_the_same_run_twice_is_idempotent_and_the_second_makes_no_detail_requests(session_factory, pols):
    p1, p2 = Fake([B(1), B(2, subjects=["A", "B"])]), Fake([B(1), B(2, subjects=["A", "B"])])
    run(session_factory, p1)
    first = dump(session_factory)
    r = run(session_factory, p2)
    assert dump(session_factory) == first
    assert (r.bills_unchanged, r.bills_fetched, r.bills_inserted, r.bills_updated) == (2, 0, 0, 0) and p2.detail_calls == 0
    assert r.requests == 2  # only the two list requests (bills and hearings)


def test_a_forced_rerun_rewrites_nothing_new(session_factory, pols):
    bills = [B(1, cosponsors=[leg.BillCosponsor("S000001", "x", date(2026, 5, 11), False, None)]), B(2)]
    run(session_factory, Fake(bills))
    before = dump(session_factory)
    r = run(session_factory, Fake(bills), force=True)
    assert dump(session_factory) == before and (r.bills_updated, r.bills_inserted, r.actions_inserted, r.subjects_inserted, r.links_inserted) == (2, 0, 0, 0, 0)


def test_unchanged_bills_updated_today_are_still_re_read(session_factory, pols):
    run(session_factory, Fake([B(1, update=TODAY)]))
    again = run(session_factory, Fake([B(1, update=TODAY)]))
    assert again.bills_unchanged == 0 and again.bills_updated == 1  # Congress.gov can change a record twice in one day


def test_duplicate_subjects_committees_actions_and_links_from_the_provider_are_stored_once(session_factory, pols):
    act = leg.BillAction(date(2026, 5, 10), "Referred", "H1", "t")
    cos = leg.BillCosponsor("S000001", "x", date(2026, 5, 11), True, None)
    cmte = leg.CommitteeRef("hsif00", "Energy and Commerce Committee", "House")
    r = run(session_factory, Fake([B(1, subjects=["A", "A"], actions=[act, act], cosponsors=[cos, cos], committees=[cmte, cmte])]))
    assert (count(session_factory, LegislationSubject), count(session_factory, BillAction), count(session_factory, LegislationCommittee)) == (1, 1, 1)
    assert count(session_factory, PoliticianLegislation) == 2 and r.subjects_inserted == 1 and r.actions_inserted == 1  # sponsor + one cosponsor link


def test_an_updated_bill_gains_new_actions_and_syncs_subjects_committees_and_cosponsors(session_factory, pols):
    cos = leg.BillCosponsor("S000001", "x", date(2026, 5, 11), True, None)
    run(session_factory, Fake([B(1, subjects=["A", "B"], cosponsors=[cos])]))
    new_action = leg.BillAction(date(2026, 6, 1), "Passed House", "H8", "Floor")
    updated = B(1, subjects=["B", "C"], committees=[], cosponsors=[], update=TODAY - timedelta(days=1), latest=date(2026, 6, 1))
    updated.actions = updated.actions + [new_action]
    r = run(session_factory, Fake([updated]))
    with session_factory() as s:
        row = s.scalar(select(Legislation))
        assert {x.subject for x in row.subjects} == {"B", "C"} and row.committees == [] and len(row.actions) == 2
        assert [(l.relationship_type) for l in row.politician_links] == ["sponsor"]  # the cosponsor is gone from the official record
        assert row.latest_action_date == date(2026, 6, 1)
    assert (r.actions_inserted, r.subjects_inserted) == (1, 1)


# --- politician links -----------------------------------------------------------------------------------------

def test_sponsor_and_cosponsors_link_to_existing_politicians_by_bioguide_id(session_factory, pols):
    cos = [leg.BillCosponsor("S000001", "Sen. Pat", date(2026, 5, 11), True, None), leg.BillCosponsor("D000399", "Rep. D", date(2026, 5, 12), False, date(2026, 6, 1))]
    run(session_factory, Fake([B(1, cosponsors=cos)]))
    with session_factory() as s:
        links = {(l.politician_id, l.relationship_type): l for l in s.scalars(select(PoliticianLegislation))}
    assert set(links) == {(pols["a"], "sponsor"), (pols["b"], "cosponsor"), (pols["a"], "cosponsor")}  # one politician may be both
    assert links[(pols["a"], "sponsor")].sponsorship_date == date(2026, 5, 10)
    assert (links[(pols["b"], "cosponsor")].is_original, links[(pols["b"], "cosponsor")].withdrawn_date) == (True, None)
    assert links[(pols["a"], "cosponsor")].withdrawn_date == date(2026, 6, 1)  # withdrawn cosponsors stay recorded, dated


def test_an_unknown_bioguide_id_creates_no_politician_and_keeps_the_legislative_record(session_factory, pols):
    before = count(session_factory, Politician)
    cos = [leg.BillCosponsor("X999999", "Rep. Stranger", date(2026, 5, 11), True, None)]
    r = run(session_factory, Fake([B(1, sponsor=leg.BillSponsor("Z000001", "Rep. Unknown [R-ZZ-1]", "R", "ZZ"), cosponsors=cos)]))
    assert count(session_factory, Politician) == before and count(session_factory, PoliticianLegislation) == 0
    assert r.sponsors_not_in_poltracker == 1 and r.bills_inserted == 1
    with session_factory() as s:
        row = s.scalar(select(Legislation))
        assert (row.sponsor_bioguide_id, row.sponsor_name) == ("Z000001", "Rep. Unknown [R-ZZ-1]")  # the official sponsor is still recorded


def test_names_are_never_matched_only_bioguide_ids(session_factory, pols):
    # A cosponsor with exactly a POLTRACKER politician's name but a different (or no) Bioguide ID must not be linked.
    cos = [leg.BillCosponsor("R000999", "Lloyd Doggett", date(2026, 5, 11), True, None), leg.BillCosponsor("J000001", "Jane Roe", date(2026, 5, 11), True, None)]
    run(session_factory, Fake([B(1, sponsor=leg.BillSponsor("N000001", "Pat Senator", "D", "ZZ"), cosponsors=cos)]))
    assert count(session_factory, PoliticianLegislation) == 0


# --- scope: the date window -----------------------------------------------------------------------------------

def test_only_bills_with_an_action_inside_the_window_are_stored_and_only_in_window_actions(session_factory, pols):
    inside = B(1, latest=date(2026, 6, 1), actions=[leg.BillAction(date(2024, 3, 1), "Introduced long ago", "a", "t"), leg.BillAction(date(2026, 6, 1), "Reported", "b", "t")])
    outside = B(2, latest=date(2026, 6, 1), actions=[leg.BillAction(date(2024, 3, 1), "Old only", "a", "t")])
    r = run(session_factory, Fake([inside, outside]))
    assert (r.bills_fetched, r.bills_out_of_scope) == (1, 1) and count(session_factory, Legislation) == 1
    with session_factory() as s:
        assert [a.action_text for a in s.scalars(select(BillAction))] == ["Reported"]  # the 2024 action is outside the window


def test_a_bill_whose_latest_action_predates_the_window_costs_no_detail_requests(session_factory, pols):
    old = B(1, latest=date(2024, 12, 1), update=OLD)
    p = Fake([old])
    r = run(session_factory, p, hearings=False)
    assert r.bills_before_window == 1 and p.detail_calls == 0 and p.requests_made == 1 and count(session_factory, Legislation) == 0


def test_window_edges_are_inclusive_and_actions_after_the_window_end_are_excluded(session_factory, pols):
    acts = [leg.BillAction(FROM, "first day", "a", "t"), leg.BillAction(TO, "last day", "b", "t"), leg.BillAction(TO + timedelta(days=1), "after", "c", "t"),
            leg.BillAction(FROM - timedelta(days=1), "before", "d", "t")]
    run(session_factory, Fake([B(1, actions=acts, latest=TO + timedelta(days=1))]))
    with session_factory() as s:
        assert sorted(a.action_text for a in s.scalars(select(BillAction))) == ["first day", "last day"]


def test_a_narrow_custom_window_is_respected(session_factory, pols):
    bills = [B(1, latest=date(2026, 3, 1), actions=[leg.BillAction(date(2026, 3, 1), "march", "a", "t")]),
             B(2, latest=date(2026, 8, 1), actions=[leg.BillAction(date(2026, 8, 1), "august", "b", "t")])]
    r = run(session_factory, Fake(bills), from_date=date(2026, 7, 1), to_date=date(2026, 9, 1))
    assert r.bills_inserted == 1
    with session_factory() as s:
        assert s.scalar(select(Legislation.bill_number)) == 2


def test_a_window_spanning_two_congresses_lists_both(session_factory, pols):
    bills = [B(1, congress=118, latest=date(2024, 6, 1), actions=[leg.BillAction(date(2024, 6, 1), "x", "a", "t")]), B(2)]
    r = run(session_factory, Fake(bills), from_date=date(2024, 1, 1))
    assert r.bills_inserted == 2


def test_an_inverted_window_is_refused(session_factory, pols):
    r = run(session_factory, Fake([B(1)]), from_date=TO, to_date=FROM)
    assert r.status == "provider_error" and "after" in r.message and count(session_factory, Legislation) == 0


def test_the_default_window_follows_the_trade_range_but_never_precedes_the_current_congress(session_factory, pols):
    assert default_window(session_factory, TODAY, 30) == (date(2026, 5, 1) - timedelta(days=30), TODAY)  # the earliest trade minus a buffer
    with session_factory() as s:
        s.add(Trade(source="t", fingerprint="old", politician_id=pols["a"], politician_name="x", chamber="house", transaction_type="buy", transaction_date=date(2023, 10, 31)))
        s.add(Trade(source="t", fingerprint="bad", politician_id=pols["a"], politician_name="x", chamber="house", transaction_type="buy", transaction_date=date(2026, 12, 26)))
        s.commit()
    assert default_window(session_factory, TODAY, 30) == (date(2025, 1, 3), TODAY)  # clamped to the 119th Congress; the future date is ignored


def test_with_no_trades_the_default_window_is_the_last_year(session_factory):
    assert default_window(session_factory, TODAY, 30) == (date(2025, 10, 7), TODAY)


# --- hearings -------------------------------------------------------------------------------------------------

def test_hearings_inside_the_window_are_stored_with_committees_and_others_are_not(session_factory, pols):
    cm = [leg.CommitteeRef("hsag00", "Agriculture Committee"), leg.CommitteeRef("hsag00", "Agriculture Committee")]
    hs = [hearing(1, date(2026, 3, 4), date(2026, 3, 5), committees=cm), hearing(2, date(2024, 1, 1)), hearing(3), hearing(4, date(2026, 10, 8))]
    r = run(session_factory, Fake([], hs))
    assert (r.hearings_listed, r.hearings_inserted, r.hearings_out_of_scope) == (4, 1, 3)
    with session_factory() as s:
        h = s.scalar(select(Hearing))
        assert (h.jacket_number, h.hearing_date, h.hearing_end_date, h.citation, h.source_url) == (1, date(2026, 3, 4), date(2026, 3, 5), "CIT-1", "https://api.congress.gov/v3/hearing/119/house/1")
        assert [(c.committee_code, c.committee_name) for c in h.committees] == [("hsag00", "Agriculture Committee")]  # duplicate collapsed


def test_a_hearing_without_committee_data_stays_without_it(session_factory, pols):
    run(session_factory, Fake([], [hearing(9, date(2026, 3, 4))]))
    assert count(session_factory, Hearing) == 1 and count(session_factory, HearingCommittee) == 0


def test_hearings_are_idempotent_and_unchanged_ones_are_not_refetched(session_factory, pols):
    hs = [hearing(1, date(2026, 3, 4))]
    run(session_factory, Fake([], hs))
    p = Fake([], hs)
    r = run(session_factory, p)
    assert (r.hearings_unchanged, r.hearings_inserted, r.hearings_updated) == (1, 0, 0) and count(session_factory, Hearing) == 1 and p.requests_made == 2  # two list calls (bills, hearings)
    changed = [hearing(1, date(2026, 3, 4), update=datetime(2026, 9, 15))]
    assert run(session_factory, Fake([], changed)).hearings_updated == 1 and count(session_factory, Hearing) == 1


def test_hearings_can_be_skipped(session_factory, pols):
    r = run(session_factory, Fake([B(1)], [hearing(1, date(2026, 3, 4))]), hearings=False)
    assert r.hearings_listed == 0 and count(session_factory, Hearing) == 0 and count(session_factory, Legislation) == 1


# --- dry run, limits, failures --------------------------------------------------------------------------------

def test_a_dry_run_reports_exactly_what_a_real_run_would_do_and_writes_nothing(session_factory, pols):
    bills = [B(1, cosponsors=[leg.BillCosponsor("S000001", "x", date(2026, 5, 11), True, None)]), B(2, subjects=["A", "B"])]
    hs = [hearing(1, date(2026, 3, 4), committees=[leg.CommitteeRef("hsag00", "Ag")])]
    dry = run(session_factory, Fake(bills, hs), dry_run=True)
    assert dump(session_factory) == {k: [] for k in dump(session_factory)}  # not one row in any legislative table
    assert (count(session_factory, Legislation), count(session_factory, Hearing), count(session_factory, BillAction)) == (0, 0, 0)
    real = run(session_factory, Fake(bills, hs))
    for name in ("bills_inserted", "subjects_inserted", "committees_inserted", "actions_inserted", "links_inserted", "hearings_inserted", "bills_fetched"):
        assert getattr(dry, name) == getattr(real, name), name
    assert dry.dry_run and "nothing written" in dry.summary()


def test_the_limit_bounds_how_many_bills_are_considered(session_factory, pols):
    bills = [B(n, update=OLD - timedelta(days=n)) for n in range(1, 8)]
    p = Fake(bills)
    r = run(session_factory, p, limit=3)
    assert r.bills_fetched == 3 and count(session_factory, Legislation) == 3 and p.detail_calls == 3


def test_one_bad_bill_is_reported_and_leaves_no_partial_rows_while_the_others_are_stored(session_factory, pols):
    r = run(session_factory, Fake([B(1), B(2), B(3)], bad={2}))
    assert r.bills_fetched == 2 and len(r.errors) == 1 and "HR2/119" in r.errors[0]
    with session_factory() as s:
        assert sorted(s.scalars(select(Legislation.bill_number))) == [1, 3]


def test_a_rate_limit_stops_the_run_but_keeps_progress_and_a_rerun_continues(session_factory, pols):
    bills = [B(n, update=OLD - timedelta(days=n)) for n in range(1, 6)]
    r = run(session_factory, Fake(bills, rate_limit_at=3))
    assert r.status == "rate_limited" and "re-run" in r.message and count(session_factory, Legislation) == 2
    again = run(session_factory, Fake(bills))
    assert again.status == "ok" and count(session_factory, Legislation) == 5 and again.bills_unchanged == 2


def test_a_missing_api_key_is_reported_and_nothing_is_written(session_factory, pols):
    r = run(session_factory, Fake([B(1)], error=NotConfigured("CONGRESS_API_KEY is not set")))
    assert r.status == "not_configured" and "CONGRESS_API_KEY" in r.message and count(session_factory, Legislation) == 0


# --- existing data is never touched ---------------------------------------------------------------------------

def test_existing_politicians_trades_securities_and_prices_are_untouched(session_factory, pols):
    def snap():
        with session_factory() as s:
            return [sorted(s.execute(text(q)).all()) for q in (
                "select * from politicians", "select * from trades", "select * from securities", "select * from price_bars", "select * from committee_assignments")]

    before = snap()
    cos = [leg.BillCosponsor("S000001", "x", date(2026, 5, 11), True, None), leg.BillCosponsor("Q000001", "unknown", None, False, None)]
    run(session_factory, Fake([B(1, cosponsors=cos), B(2)], [hearing(1, date(2026, 3, 4))]))
    run(session_factory, Fake([B(1, cosponsors=cos), B(2)], [hearing(1, date(2026, 3, 4))]), force=True)
    assert snap() == before


def test_a_dry_run_leaves_a_real_sqlite_file_byte_for_byte_unchanged(tmp_path):
    import hashlib

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from poltracker.models import Base

    path = tmp_path / "real.db"
    engine = create_engine(f"sqlite:///{path}")  # a file database, like the real app's, not the in-memory test fixture
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as s:
        s.add(Politician(canonical_key="house:a", name="A", chamber="house", bioguide_id="D000399"))
        s.commit()
    engine.dispose()
    sha = lambda: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
    before = sha()
    engine = create_engine(f"sqlite:///{path}")
    factory = sessionmaker(engine, expire_on_commit=False)
    report = run(factory, Fake([B(1), B(2)], [hearing(1, date(2026, 3, 4))]), dry_run=True)
    engine.dispose()
    assert report.bills_inserted == 2 and report.hearings_inserted == 1 and sha() == before
    engine = create_engine(f"sqlite:///{path}")
    factory = sessionmaker(engine, expire_on_commit=False)
    run(factory, Fake([B(1), B(2)], [hearing(1, date(2026, 3, 4))]))  # and a real run on the same file does write
    assert count(factory, Legislation) == 2 and count(factory, Hearing) == 1
