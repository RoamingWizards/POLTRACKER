"""Committee seat history from adopted House resolutions: parsing, name matching, intervals, storage, the provider, and the effect on context signals."""

import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from poltracker.committee_history import (
    PRECISION_EXACT, build_events, build_intervals, candidates, congress_of, parse_names, parse_resolution, parse_roster,
)
from poltracker.config import get_settings
from poltracker.enrich_committee_history import sync_history
from poltracker.models import CommitteeAssignment, CommitteeIndustryMapping, Politician, Security, Trade, TradeContext
from poltracker.providers.base import ProviderError
from poltracker.providers.house_resolutions import HouseResolutionsProvider
from poltracker.trade_context import ContextConfig

from test_trade_context import A, ROOT, SRC, TODAY, run  # noqa: E402

CLERK = """<?xml version="1.0"?><MemberData publish-date="October 1, 2026"><title-info><congress-num>119</congress-num></title-info><members>
<member><member-info><bioguideID>R000575</bioguideID><lastname>Rogers</lastname><firstname>Mike</firstname><official-name>Mike Rogers</official-name><formal-name>Mr. Rogers of Alabama</formal-name>
 <state postal-code="AL"><state-fullname>Alabama</state-fullname></state><prior-congress>118</prior-congress><sworn-date date="20250103"/></member-info>
 <committee-assignments><committee comcode="AS00"/><subcommittee subcomcode="AS25"/></committee-assignments></member>
<member><member-info><bioguideID>R000620</bioguideID><lastname>Rogers</lastname><firstname>Harold</firstname><official-name>Hal Rogers</official-name><formal-name>Mr. Rogers of Kentucky</formal-name>
 <state postal-code="KY"><state-fullname>Kentucky</state-fullname></state><sworn-date date="20250103"/></member-info><committee-assignments><committee comcode="AP00"/></committee-assignments></member>
<member><member-info><bioguideID>C001123</bioguideID><lastname>Cisneros</lastname><firstname>Gilbert</firstname><official-name>Gil Cisneros</official-name><formal-name>Mr. Cisneros</formal-name>
 <state postal-code="CA"><state-fullname>California</state-fullname></state><prior-congress>116</prior-congress><sworn-date date="20250103"/></member-info>
 <committee-assignments><committee comcode="AS00"/></committee-assignments></member>
<member><member-info><bioguideID>G000551</bioguideID><lastname>Gonzales</lastname><firstname>Anthony</firstname><official-name>Tony Gonzales</official-name><formal-name>Mr. Tony Gonzales of Texas</formal-name>
 <state postal-code="TX"><state-fullname>Texas</state-fullname></state><sworn-date date="20250103"/></member-info><committee-assignments><committee comcode="AS00"/></committee-assignments></member>
<member><member-info><bioguideID>N000999</bioguideID><lastname>Newman</lastname><firstname>Nora</firstname><official-name>Nora Newman</official-name><formal-name>Ms. Newman</formal-name>
 <state postal-code="NY"><state-fullname>New York</state-fullname></state><sworn-date date="20260301"/></member-info><committee-assignments><committee comcode="AS00"/></committee-assignments></member>
<member><member-info><namelist/><bioguideID/><lastname/><firstname/><state postal-code="TX"><state-fullname>Texas</state-fullname></state></member-info>
 <predecessor-info cause="R"><pred-lastname>Cisneros</pred-lastname><pred-firstname>Other</pred-firstname><pred-official-name>Other Cisneros</pred-official-name><pred-formal-name>Mr. Cisneros of Texas</pred-formal-name></predecessor-info></member>
<committees><committee comcode="AS00"><committee-fullname>Committee on Armed Services</committee-fullname><subcommittee subcomcode="AS25"><subcommittee-fullname>Sea</subcommittee-fullname></subcommittee></committee>
 <committee comcode="AP00"><committee-fullname>Committee on Appropriations</committee-fullname></committee></committees></members></MemberData>"""


def roster():
    return parse_roster(ET.fromstring(CLERK))


def resolution(day, verb, paragraphs, style="appointment", engrossed=True):
    paras = "".join(
        f"<committee-appointment-paragraph><header>{h}:</header><text>{t}</text></committee-appointment-paragraph>" if style == "appointment"
        else f"<paragraph><enum>(1)</enum><header>{h}</header><text>{t}</text></paragraph>" for h, t in paragraphs)
    head = f"In the House of Representatives, U. S., {day}" if engrossed else f"IN THE HOUSE OF REPRESENTATIVES {day}"
    return (f"<resolution><form><action>{head}</action></form><resolution-body><section><text>That the following named Members be, and are hereby, {verb} "
            f"the following standing committees of the House of Representatives:</text>{paras}</section></resolution-body></resolution>")


# --- the Clerk roster, Congresses and names -------------------------------------------------------------------------

def test_the_roster_reads_the_snapshot_date_congress_names_and_departed_members():
    r = roster()
    assert r.snapshot_date == date(2026, 10, 1) and r.congress_number == 119 and r.committees == {"AS00": "Committee on Armed Services", "AP00": "Committee on Appropriations"}
    assert ("R000575", "AS00") in r.seats and ("R000575", "AP00") not in r.seats  # full-committee seats only
    assert any(m.bioguide_id is None and m.last == "Cisneros" for m in r.members)  # a member who left is kept so a surname is never guessed


@pytest.mark.parametrize("d,n", [(date(2025, 1, 2), 118), (date(2025, 1, 3), 119), (date(2026, 12, 31), 119), (date(2027, 1, 3), 120), (date(2023, 1, 3), 118), (date(2024, 11, 26), 118)])
def test_congress_of_follows_the_constitutional_calendar(d, n):
    assert congress_of(d) == n


def test_names_are_read_without_the_rank_phrases_chair_titles_or_parentheticals():
    names, odd = parse_names("Mr. Rogers of Alabama, Chair, Ms. Foxx (to rank immediately after Mr. Strong), Mr. Tony Gonzales of Texas, Mrs. Biggs of South Carolina.")
    assert names == [("Rogers", "Alabama"), ("Foxx", None), ("Tony Gonzales", "Texas"), ("Biggs", "South Carolina")] and odd == []
    names, _ = parse_names("Mr. Menefee, to rank immediately after Mr. Riley of New York.")
    assert names == [("Menefee", None)]
    assert parse_names("Ms. Chu to rank immediately after Ms. Jayapal.")[0] == [("Chu", None)]
    assert parse_names("the Delegate from Guam")[1] == ["the Delegate from Guam"]


def test_a_name_is_matched_to_one_member_or_set_aside_never_guessed():
    members, on = roster().members, date(2025, 2, 1)
    assert [m.bioguide_id for m in candidates("Rogers", "Alabama", members, on)] == ["R000575"]
    assert len(candidates("Rogers", None, members, on)) == 2  # two sitting Rogers: ambiguous without a state
    assert [m.bioguide_id for m in candidates("Tony Gonzales", "Texas", members, on)] == ["G000551"]  # first name as the House uses it
    assert candidates("Mark Gonzales", "Texas", members, on) == []  # a first name that is not this member's
    assert candidates("Newman", None, members, on) == [] and [m.bioguide_id for m in candidates("Newman", None, members, date(2026, 4, 1))] == ["N000999"]  # not before being sworn in
    assert {m.bioguide_id for m in candidates("Cisneros", None, members, on)} == {"C001123", None}  # a departed namesake makes it ambiguous


# --- resolutions ---------------------------------------------------------------------------------------------------

def test_only_an_engrossed_resolution_with_an_adoption_date_is_read_in_either_paragraph_style():
    for style in ("appointment", "numbered"):
        doc = parse_resolution(resolution("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Cisneros")], style))
        assert doc["date"] == date(2025, 1, 14) and doc["verb"] == "elected" and doc["paragraphs"] == [("Committee on Armed Services", "Mr. Cisneros")]
    assert parse_resolution(resolution("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Cisneros")], engrossed=False)) is None  # introduced, not adopted
    assert parse_resolution("<not-xml") is None
    assert parse_resolution(resolution("March 1, 2025", "removed from", [("Committee on Armed Services", "Mr. Cisneros")]))["verb"] == "removed"


def docs(*items):
    return [(f"H.Res. {i}", f"https://example/{i}", resolution(*it).encode()) for i, it in enumerate(items, start=1)]


def test_events_are_placed_on_members_and_unplaceable_names_are_reported_not_guessed():
    d = docs(("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Cisneros, Mr. Rogers of Alabama, Mr. Rogers, Mr. Nobody"), ("Committee on Ghosts", "Mr. Cisneros")]))
    events, rep = build_events(d, roster())
    got = {(e.bioguide_id, e.committee_code) for e in events}
    assert ("R000575", "AS00") in got and ("C001123", "AS00") not in got  # "Mr. Cisneros" has a departed namesake: set aside
    assert rep.ambiguous_names == 2 and rep.unresolved_names == 1 and rep.unmapped_committees == {"Committee on Ghosts"} and {"R000575", "R000620", "C001123"} <= rep.ambiguous_members


def build(*items, snapshot_seats=None):
    r = roster()
    events, rep = build_events(docs(*items), r)
    return build_intervals(events, r, rep.ambiguous_members), r


def test_an_election_with_no_removal_is_open_and_confirmed_only_up_to_the_snapshot():
    iv, _ = build(("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    assert len(iv) == 1 and iv[0].start == date(2025, 1, 14) and iv[0].end is None and iv[0].verified_through == date(2026, 10, 1) and iv[0].history_complete


def test_a_removal_closes_the_interval_and_a_seat_missing_from_the_snapshot_is_not_confirmed():
    iv, _ = build(("January 14, 2025", "elected to", [("Committee on Appropriations", "Mr. Rogers of Alabama"), ("Committee on Armed Services", "Mr. Rogers of Alabama")]),
                  ("June 2, 2025", "removed from", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    by = {i.committee_code: i for i in iv}
    assert (by["AS00"].start, by["AS00"].end, by["AS00"].history_complete) == (date(2025, 1, 14), date(2025, 6, 2), True)
    assert by["AP00"].end is None and by["AP00"].verified_through is None  # Mike Rogers is not on the full Appropriations committee in the snapshot: no confirmation


def test_double_elections_and_orphan_removals_make_a_record_incomplete_so_it_can_never_prove_absence():
    iv, _ = build(("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]),
                  ("March 3, 2025", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    assert len(iv) == 1 and iv[0].start == date(2025, 3, 3) and not iv[0].history_complete and "continuity not established" in iv[0].note  # counts from the later election
    iv, _ = build(("March 3, 2025", "removed from", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    assert iv == []  # nothing to open, and the orphan removal is not turned into a seat


# --- storage -------------------------------------------------------------------------------------------------------

def seed_people(factory):
    with factory() as s:
        rogers = Politician(canonical_key="mr", name="Mike Rogers", chamber="house", bioguide_id="R000575")
        cis = Politician(canonical_key="gc", name="Gil Cisneros", chamber="house", bioguide_id="C001123")
        other = Politician(canonical_key="zz", name="Zed", chamber="house", bioguide_id="Z000001")
        s.add_all([rogers, cis, other])
        s.flush()
        for p in (rogers, cis):
            s.add(CommitteeAssignment(politician_id=p.id, committee_name="Committee on Armed Services", committee_code="AS00", subcommittee_code="", chamber="house", source="house.clerk",
                                      temporal_precision="current_snapshot", source_type="house_clerk_member_data"))
        s.commit()
        return {"rogers": rogers.id, "cis": cis.id, "other": other.id}


D = docs(("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama, Mr. Tony Gonzales of Texas")]))
D = [(l, f"https://www.govinfo.gov/content/pkg/BILLS-119hres{i}eh/xml/x.xml", x) for i, (l, u, x) in enumerate(D, start=1)]


def test_history_is_written_only_for_the_politicians_in_scope_and_the_snapshot_gets_its_provenance(session_factory):
    ids = seed_people(session_factory)
    rep = sync_history(session_factory, roster(), D, 119, scope="all", now=datetime(2026, 10, 9))
    assert rep.politicians_in_scope == 3 and rep.politicians_with_history == 1 and rep.intervals_written == 1
    with session_factory() as s:
        rows = s.scalars(select(CommitteeAssignment).where(CommitteeAssignment.source == "house.resolutions")).all()
        assert len(rows) == 1 and rows[0].politician_id == ids["rogers"] and rows[0].committee_code == "AS00" and rows[0].subcommittee_code == ""
        assert (rows[0].start_date, rows[0].end_date, rows[0].temporal_precision, rows[0].source_type, rows[0].congress_number) == (date(2025, 1, 14), None, PRECISION_EXACT, "house_resolution", 119)
        assert rows[0].verified_through == date(2026, 10, 1) and rows[0].history_complete is True and rows[0].source_url.startswith("https://www.govinfo.gov/")
        snap = s.scalars(select(CommitteeAssignment).where(CommitteeAssignment.source == "house.clerk")).all()
        assert all(r.congress_number == 119 and r.verified_through == date(2026, 10, 1) and r.start_date is None and r.temporal_precision == "current_snapshot" for r in snap)  # no dates invented


def test_the_sync_is_idempotent_and_a_dry_run_writes_nothing(session_factory):
    seed_people(session_factory)
    dry = sync_history(session_factory, roster(), D, 119, scope="all", dry_run=True)
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(CommitteeAssignment).where(CommitteeAssignment.source == "house.resolutions")) == 0
    sync_history(session_factory, roster(), D, 119, scope="all")
    sync_history(session_factory, roster(), D, 119, scope="all")
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(CommitteeAssignment).where(CommitteeAssignment.source == "house.resolutions")) == 1
        assert s.scalar(select(func.count()).select_from(CommitteeAssignment).where(CommitteeAssignment.source == "house.clerk")) == 2  # snapshot rows untouched in number
    assert dry.intervals_written == 1


def test_scope_committee_relevant_selects_politicians_with_a_committee_relevant_trade(session_factory):
    ids = seed_people(session_factory)
    with session_factory() as s:
        sec = Security(ticker="BA", sic_code="3721", industry="Aircraft")
        s.add(sec)
        s.flush()
        t = Trade(source="t", fingerprint="f", politician_id=ids["rogers"], security_id=sec.id, politician_name="Mike Rogers", chamber="house", ticker="BA", transaction_type="buy",
                  transaction_date=date(2026, 2, 1), amount_min=1001, amount_max=15000)
        s.add(t)
        s.flush()
        s.add(TradeContext(trade_id=t.id, context_version=ContextConfig().version_label(), mapping_version="v1", result_digest="d", analyzed_at=datetime(2026, 10, 1), committee_relevance=True,
                           signal_count=1, flagged_for_contextual_review=False))
        s.commit()
    rep = sync_history(session_factory, roster(), D, 119, scope="committee-relevant")
    assert rep.politicians_in_scope == 1 and rep.politicians_with_history == 1


# --- the effect on context signals ------------------------------------------------------------------------------------

def seed_trades(factory, ids, rogers_start):
    """A reviewed-direct mapping for AS00; one big aircraft trade by Mike Rogers on 2026-02-20 that is also late and unusually large."""
    from poltracker.models import CommitteeIndustryMapping as CIM

    with factory() as s:
        sec = Security(ticker="BA", sic_code="3721", industry="Aircraft")
        plain = Security(ticker="KO", sic_code="2086", industry="Soft Drinks")
        s.add_all([sec, plain])
        s.add(CIM(chamber="house", committee_code="AS00", committee_name="Armed Services", sic_start=3720, sic_end=3729, relevance_level="direct", rationale="aircraft", source_url=SRC,
                  mapping_version="v1", review_status="reviewed", reviewed_at=datetime(2026, 10, 1), jurisdiction_basis="rule_x_text"))
        s.flush()
        for i in range(12):
            s.add(Trade(source="t", fingerprint=f"p{i}", politician_id=ids["rogers"], security_id=plain.id, politician_name="Mike Rogers", chamber="house", ticker="KO", transaction_type="buy",
                        transaction_date=date(2026, 1, 1 + i), disclosure_date=date(2026, 1, 5 + i), amount_min=1001, amount_max=15000))
        big = Trade(source="t", fingerprint="big", politician_id=ids["rogers"], security_id=sec.id, politician_name="Mike Rogers", chamber="house", ticker="BA", transaction_type="buy",
                    transaction_date=date(2026, 2, 20), disclosure_date=date(2026, 4, 20), amount_min=250001, amount_max=500000)
        s.add(big)
        s.commit()
        return big.id


def test_end_to_end_a_seat_the_resolutions_show_began_after_the_trade_is_rejected(session_factory):
    ids = seed_people(session_factory)
    big = seed_trades(session_factory, ids, None)
    late = docs(("May 5, 2026", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    sync_history(session_factory, roster(), [(l, f"https://www.govinfo.gov/content/pkg/BILLS-119hres{i}eh/x.xml", x) for i, (l, u, x) in enumerate(late, start=1)], 119, scope="all")
    summary = run(session_factory)
    assert summary.contradicted == 1 and summary.committee[True] == 0 and summary.flagged == 0
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == big))
        assert (c.committee_relevance, c.committee_temporal_status, c.committee_relevance_reason) == (False, "contradicted", "seat_not_held_on_transaction_date")
        assert c.flagged_for_contextual_review is False and c.secondary_signal_count == 2
        ev = [(e.evidence_type, e.committee_code) for e in c.evidence if e.signal_type == "committee_relevance"]
        assert ev == [("rejected_current_assignment", "AS00")]


def test_end_to_end_a_seat_the_resolutions_show_was_held_makes_the_match_verified_and_flaggable(session_factory):
    ids = seed_people(session_factory)
    big = seed_trades(session_factory, ids, None)
    held = docs(("January 14, 2025", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]))
    sync_history(session_factory, roster(), [(l, f"https://www.govinfo.gov/content/pkg/BILLS-119hres{i}eh/x.xml", x) for i, (l, u, x) in enumerate(held, start=1)], 119, scope="all")
    summary = run(session_factory)
    assert summary.flagged == 1 and summary.contradicted == 0 and summary.committee_level_verified == 1 and summary.committee_level_trades == 1
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == big))
        assert (c.committee_relevance, c.committee_temporal_status, c.flagged_for_contextual_review) == (True, "temporally_verified", True)


def test_without_dated_history_the_match_stays_current_assignment_only_and_nothing_is_flagged(session_factory):
    ids = seed_people(session_factory)
    seed_trades(session_factory, ids, None)
    summary = run(session_factory)
    assert summary.committee[True] == 1 and summary.contradicted == 0 and summary.flagged == 0 and summary.pending_temporal == 1


# --- the provider -------------------------------------------------------------------------------------------------

def make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


def test_the_provider_returns_only_engrossed_resolutions_and_caches_the_bulk_files(tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "/1/hres/" in str(request.url):
            return httpx.Response(200, content=make_zip({"BILLS-119hres13eh.xml": "<a/>", "BILLS-119hres14ih.xml": "<b/>", "BILLS-119hres30eh.xml": "<c/>"}))
        return httpx.Response(404)  # the second session has not happened

    provider = HouseResolutionsProvider(httpx.Client(transport=httpx.MockTransport(handler)), cache_dir=tmp_path, pause=0)
    docs_ = provider.engrossed_documents(119)
    assert [d[0] for d in docs_] == ["H.Res. 13", "H.Res. 30"] and docs_[0][1].endswith("BILLS-119hres13eh.xml") and len(calls) == 2
    again = HouseResolutionsProvider(httpx.Client(transport=httpx.MockTransport(handler)), cache_dir=tmp_path, pause=0).engrossed_documents(119)
    assert [d[0] for d in again] == ["H.Res. 13", "H.Res. 30"] and len(calls) == 3  # only the missing second session was asked for again


def test_the_provider_retries_then_reports_a_provider_error(tmp_path):
    def handler(request):
        return httpx.Response(503)

    provider = HouseResolutionsProvider(httpx.Client(transport=httpx.MockTransport(handler)), attempts=2, pause=0)
    with pytest.raises(ProviderError):
        provider.engrossed_documents(119)
    assert provider.requests_made == 2


# --- migration ----------------------------------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm14.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    yield sa.create_engine(url), cfg
    get_settings.cache_clear()


def test_migration_0014_marks_existing_rows_as_snapshots_and_allows_two_stints_on_a_committee(db):
    engine, cfg = db
    command.upgrade(cfg, "0013")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (1, 'a', 'A', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into committee_assignments (politician_id, committee_name, committee_code, subcommittee_code, role, chamber, source, fetched_at) "
                          "values (1, 'Armed Services', 'AS00', '', 'Member', 'house', 'house.clerk', '2026-01-01')")
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        row = c.exec_driver_sql("select start_date, temporal_precision, source_type, congress_number, verified_through, history_complete from committee_assignments").one()
        assert tuple(row) == (None, "current_snapshot", "house_clerk_member_data", None, None, None)  # nothing about the seat itself is claimed
    with engine.begin() as c:
        for start, end in (("2025-01-14", "2025-06-02"), ("2025-09-01", None)):
            c.exec_driver_sql("insert into committee_assignments (politician_id, committee_name, committee_code, subcommittee_code, role, chamber, source, start_date, end_date, fetched_at, temporal_precision) "
                              f"values (1, 'Armed Services', 'AS00', '', 'Member', 'house', 'house.resolutions', '{start}', {'NULL' if end is None else repr(end)}, '2026-01-01', 'exact_date')")
    with engine.begin() as c, pytest.raises(sa.exc.IntegrityError):
        c.exec_driver_sql("insert into committee_assignments (politician_id, committee_name, committee_code, subcommittee_code, role, chamber, source, start_date, fetched_at) "
                          "values (1, 'Armed Services', 'AS00', '', 'Member', 'house', 'house.resolutions', '2025-09-01', '2026-01-01')")  # the same stint twice
    command.downgrade(cfg, "0013")
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*), min(source) from committee_assignments").one() == (1, "house.clerk")  # the recomputable history is dropped, the snapshot stays
    command.upgrade(cfg, "head")


def test_the_models_match_the_0014_schema(db):
    from poltracker.models import Base

    engine, cfg = db
    command.upgrade(cfg, "head")
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {c["name"] for c in sa.inspect(engine).get_columns(table.name)}, table.name


# --- an earlier Congress ------------------------------------------------------------------------------------------

def test_in_an_earlier_congress_only_a_member_who_served_then_is_a_candidate():
    members = roster().members
    on = date(2024, 6, 26)  # the 118th
    assert [m.bioguide_id for m in candidates("Rogers", "Alabama", members, on, 119)] == ["R000575"]  # prior_congress 118: served then
    assert {m.bioguide_id for m in candidates("Cisneros", None, members, on, 119)} == {None}  # Gil Cisneros's last earlier service was the 116th, so only the departed namesake could be meant
    assert candidates("Newman", None, members, on, 119) == []


def test_an_earlier_congress_has_no_snapshot_confirmation_but_its_scan_can_show_a_committee_was_not_held():
    from poltracker.trade_context import committee_history_status, effective_seats

    d = date(2024, 11, 26)
    seats = [A("ED00", start=date(2024, 6, 26), congress=118, through=None),  # the 118th: elected, no removal, but nothing confirms the end
             A("IF00"), A("IF00", "IF14")]  # the current (119th) snapshot seats
    assert committee_history_status([seats[0]], d) == "unknown"  # an open seat in the 118th is not confirmed
    got = effective_seats(seats, d)
    assert got == []  # IF00 and its subcommittee seat are rejected; the unconfirmed 118th ED00 stint verifies nothing

    # the same record says nothing about a committee in the snapshot's own Congress
    assert any(a.committee_code == "IF00" for a, _ in effective_seats(seats, date(2026, 3, 1)))


def test_an_open_interval_in_an_earlier_congress_never_gets_a_snapshot_confirmation():
    r = roster()
    events, rep = build_events([("H.Res. 1", "https://x", resolution("June 26, 2024", "elected to", [("Committee on Armed Services", "Mr. Rogers of Alabama")]).encode())], r)
    iv = build_intervals(events, r, rep.ambiguous_members)
    assert len(iv) == 1 and iv[0].congress == 118 and iv[0].end is None and iv[0].verified_through is None
