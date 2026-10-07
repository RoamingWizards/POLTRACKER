"""Official provider normalization and failure handling. No live calls: httpx.MockTransport and fixtures only."""

import json
import xml.etree.ElementTree as ET
from datetime import date

import httpx
import pytest

from poltracker.providers.base import ProviderError, ProviderRateLimited
from poltracker.providers.congress_gov import CongressGovProvider, member_url, normalize_member
from poltracker.providers.house_clerk import HouseClerkProvider, parse_committees, parse_members
from poltracker.providers.politicians import NotConfigured

from conftest import FIXTURES

CG = json.loads((FIXTURES / "congress_gov_members.json").read_text())["members"]
KEY = "test-key-do-not-leak"


def cg_provider(handler, **kw):
    kw.setdefault("sleep", lambda _s: None)
    kw.setdefault("min_interval", 0)
    return CongressGovProvider(KEY, client=httpx.Client(base_url="https://api.congress.gov/v3", transport=httpx.MockTransport(handler)), **kw)


# --- Congress.gov normalization -------------------------------------------------------------------------------

def test_a_house_member_is_normalized_into_domain_fields():
    m = normalize_member(CG[1])
    assert (m.bioguide_id, m.first_name, m.last_name, m.chamber, m.party, m.state, m.district) == (
        "D000399", "Lloyd", "Doggett", "house", "D", "TX", "37")
    assert m.active is True and m.term_start_year == 2025 and m.term_end_year is None  # the most recent term
    assert m.official_url == "https://www.congress.gov/member/lloyd-doggett/D000399"
    assert m.source == "congress.gov"


def test_a_single_district_state_is_at_large_and_a_senator_has_no_district():
    assert normalize_member(CG[0]).district == "At Large"
    senator = normalize_member(CG[2])
    assert (senator.chamber, senator.state, senator.district, senator.party) == ("senate", "OR", None, "D")


def test_a_member_whose_term_has_ended_is_not_active():
    m = normalize_member(CG[3])
    assert m.active is False and m.term_end_year == 2026
    assert (m.first_name, m.middle_name, m.last_name) == ("Marjorie", "Taylor", "Greene")


def test_suffixes_and_multi_word_surnames_are_parsed_and_terms_may_be_a_plain_list():
    m = normalize_member(CG[6])
    assert (m.first_name, m.last_name, m.suffix, m.chamber) == ("Pat", "Smith Jones", "Jr.", "house")


def test_unusable_records_are_dropped_not_guessed():
    assert normalize_member(CG[7]) is None  # no name, no terms
    assert normalize_member(CG[8]) is None  # no bioguide id
    assert normalize_member({"bioguideId": "Z000001", "name": "Last, First", "terms": {"item": [{"chamber": "Joint"}]}}) is None


def test_the_member_url_is_built_from_the_stable_id():
    assert member_url("A000372", "Rick", "Allen") == "https://www.congress.gov/member/rick-allen/A000372"


# --- Congress.gov requests ------------------------------------------------------------------------------------

def test_the_roster_is_paged_and_cached_and_the_key_stays_out_of_the_url():
    seen = []

    def handler(req):
        seen.append(req)
        if req.url.params.get("offset") == "0":
            return httpx.Response(200, json={"members": CG[:2], "pagination": {"next": "x"}})
        return httpx.Response(200, json={"members": CG[2:3], "pagination": {}})

    p = cg_provider(handler)
    members = p.list_members()
    assert [m.bioguide_id for m in members] == ["B001323", "D000399", "W000779"]
    assert p.list_members(chamber="senate")[0].bioguide_id == "W000779"
    assert p.requests_made == 2  # the second call is served from the cached roster
    assert all(KEY not in str(r.url) for r in seen)
    assert all(r.headers["x-api-key"] == KEY for r in seen)
    assert seen[0].url.path == "/v3/member/congress/119"


def test_requests_are_paced():
    sleeps, clock = [], iter(range(0, 100))
    p = cg_provider(lambda r: httpx.Response(200, json={"members": CG[:1], "pagination": {"next": "x"}} if r.url.params["offset"] == "0" else {"members": []}),
                    min_interval=0.5, sleep=sleeps.append, clock=lambda: next(clock) * 0.1)
    p.list_members()
    assert sleeps and all(0 < s <= 0.5 for s in sleeps)


def test_a_missing_key_is_reported_not_raised_as_a_crash():
    p = CongressGovProvider(None, client=httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("no request without a key"))))
    assert p.configured is False
    with pytest.raises(NotConfigured):
        p.list_members()
    assert issubclass(NotConfigured, ProviderError)


def test_transient_errors_are_retried_with_backoff_then_succeed():
    calls, sleeps = [], []

    def handler(req):
        calls.append(1)
        return httpx.Response([500, 429, 200][len(calls) - 1], headers={"Retry-After": "3"}, json={"members": CG[:1], "pagination": {}})

    p = cg_provider(handler, sleep=sleeps.append)
    assert len(p.list_members()) == 1 and len(calls) == 3
    assert 3.0 in sleeps  # Retry-After is honoured


def test_persistent_failures_raise_a_clear_provider_error_after_bounded_retries():
    p = cg_provider(lambda r: httpx.Response(503), max_retries=2)
    with pytest.raises(ProviderError, match="server error"):
        p.list_members()
    assert p.requests_made == 3


def test_rate_limit_exhaustion_is_its_own_error():
    with pytest.raises(ProviderRateLimited):
        cg_provider(lambda r: httpx.Response(429), max_retries=1).list_members()


def test_a_rejected_key_is_not_retried_and_never_echoed():
    p = cg_provider(lambda r: httpx.Response(403))
    with pytest.raises(ProviderError) as exc:
        p.list_members()
    assert "rejected the API key" in str(exc.value) and KEY not in str(exc.value) and p.requests_made == 1


def test_network_errors_become_provider_errors_without_the_url():
    def boom(req):
        raise httpx.ConnectError("no route", request=req)

    with pytest.raises(ProviderError) as exc:
        cg_provider(boom, max_retries=0).list_members()
    assert KEY not in str(exc.value) and "network error" in str(exc.value)


def test_get_member_normalizes_the_detail_shape_and_maps_404_to_none():
    detail = {"member": {"firstName": "Lloyd", "lastName": "Doggett", "state": "Texas", "district": 37, "partyHistory": [
        {"partyName": "Democratic", "startYear": 1995}], "terms": [{"chamber": "House of Representatives", "startYear": 2025}]}}

    def handler(req):
        return httpx.Response(200, json=detail) if req.url.path.endswith("D000399") else httpx.Response(404)

    p = cg_provider(handler)
    m = p.get_member("D000399")
    assert (m.bioguide_id, m.party, m.state, m.district, m.chamber) == ("D000399", "D", "TX", "37", "house")
    assert p.get_member("X999999") is None


def test_search_member_returns_candidates_only():
    p = cg_provider(lambda r: httpx.Response(200, json={"members": CG, "pagination": {}}))
    assert {m.bioguide_id for m in p.search_member("Mike Johnson", chamber="house")} == {"J000299", "J000999"}
    assert p.search_member("Mike Johnson", chamber="house", state="OH")[0].bioguide_id == "J000999"


# --- House Clerk (official roster + committees) ---------------------------------------------------------------

@pytest.fixture(scope="module")
def clerk_root():
    return ET.fromstring((FIXTURES / "house_clerk_member_data.xml").read_bytes())


def test_clerk_members_are_normalized(clerk_root):
    by_id = {m.bioguide_id: m for m in parse_members(clerk_root)}
    assert set(by_id) == {"B001323", "D000399", "M001205"}
    begich = by_id["B001323"]
    assert (begich.first_name, begich.last_name, begich.suffix, begich.state, begich.district, begich.party) == (
        "Nicholas", "Begich", "III", "AK", "At Large", "R")
    assert begich.term_start_year is None and begich.active is True and begich.source == "house.clerk"
    assert by_id["M001205"].middle_name == "D."  # kept for matching; initials are ignored there


def test_clerk_committees_and_subcommittees_are_normalized(clerk_root):
    seats = parse_committees(clerk_root)["B001323"]
    full = [s for s in seats if not s.subcommittee_code]
    subs = [s for s in seats if s.subcommittee_code]
    assert {s.committee_code for s in full} == {"II00", "PW00", "SY00"}
    assert all(s.committee_name.startswith("Committee on") for s in full) and all(s.role == "Member" for s in full if s.committee_code != "x")
    vice = next(s for s in subs if s.subcommittee_code == "II06")
    assert vice.role == "Vice Chair" and vice.committee_code == "II00" and vice.subcommittee_name
    assert vice.committee_name == next(s.committee_name for s in full if s.committee_code == "II00")
    assert all(s.chamber == "house" and s.source == "house.clerk" and s.source_url.startswith("https://clerk.house.gov") for s in seats)
    assert all(s.start_date is None for s in seats)  # the source gives no dates; none are invented


def test_clerk_vacant_seats_and_unknown_committee_codes_are_skipped():
    xml = ("<MemberData><members><member><member-info><namelist>Vacancy</namelist><bioguideID/></member-info></member>"
           "<member><member-info><bioguideID>Z1</bioguideID><firstname>A</firstname><lastname>B</lastname><party>R</party>"
           "<state postal-code='TX'/><district>1st</district></member-info><committee-assignments><committee comcode='ZZ00'/>"
           "</committee-assignments></member></members><committees/></MemberData>")
    root = ET.fromstring(xml)
    assert [m.bioguide_id for m in parse_members(root)] == ["Z1"]
    assert parse_members(root)[0].district == "1"
    assert parse_committees(root) == {}


def test_clerk_provider_downloads_once_and_filters_ids():
    body = (FIXTURES / "house_clerk_member_data.xml").read_bytes()
    hits = []
    p = HouseClerkProvider(client=httpx.Client(transport=httpx.MockTransport(lambda r: hits.append(1) or httpx.Response(200, content=body))))
    assert len(p.list_members()) == 3 and p.list_members(chamber="senate") == []
    assert set(p.get_committees({"D000399"})) == {"D000399"}
    assert p.get_member("B001323").last_name == "Begich" and p.get_member("nope") is None
    assert len(hits) == 1


@pytest.mark.parametrize("response", [httpx.Response(403, text="denied"), httpx.Response(200, content=b"<not-xml")])
def test_clerk_errors_are_provider_errors(response):
    p = HouseClerkProvider(client=httpx.Client(transport=httpx.MockTransport(lambda r: response)))
    with pytest.raises(ProviderError):
        p.list_members()
