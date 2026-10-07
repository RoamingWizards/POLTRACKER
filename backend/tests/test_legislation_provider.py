"""Congress.gov legislation provider: normalization against real-shape fixtures, pagination, retries and malformed responses."""

import json
from datetime import date, datetime

import httpx
import pytest

from poltracker.providers import legislation as leg
from poltracker.providers.base import ProviderError, ProviderRateLimited
from poltracker.providers.congress_gov import CongressGovProvider
from poltracker.providers.politicians import NotConfigured

from conftest import FIXTURES

FX = FIXTURES / "congress_gov_legislation"
KEY = "test-key-do-not-leak"


def fx(name):
    return json.loads((FX / f"{name}.json").read_text())


REF = leg.BillRef(119, "hr", 2617)


def provider(routes, **kw):
    """routes: {path suffix: dict | httpx.Response | callable(request)}; the longest matching suffix wins."""
    seen = []

    def handler(req):
        seen.append(req)
        for suffix in sorted(routes, key=len, reverse=True):
            if req.url.path.endswith(suffix):
                r = routes[suffix]
                r = r(req) if callable(r) else r
                return r if isinstance(r, httpx.Response) else httpx.Response(200, json=r)
        return httpx.Response(404)

    kw.setdefault("sleep", lambda _s: None)
    kw.setdefault("min_interval", 0)
    p = CongressGovProvider(KEY, client=httpx.Client(base_url="https://api.congress.gov/v3", transport=httpx.MockTransport(handler)), **kw)
    p.seen = seen
    return p


def first_page(name, key):
    """The recorded response for the first page only. The real responses carry a `next` link, so serving them again for the
    following offsets would loop forever; later pages are empty."""
    page = fx(name)
    return lambda req: page if req.url.params.get("offset", "0") == "0" else {key: [], "pagination": {}}


ROUTES = {
    "/bill/119": first_page("bills_list", "bills"), "/bill/119/hr/2617": fx("bill_detail"), "/bill/119/hr/2617/actions": first_page("bill_actions", "actions"),
    "/bill/119/hr/2617/subjects": fx("bill_subjects"), "/bill/119/hr/2617/summaries": first_page("bill_summaries", "summaries"),
    "/bill/119/hr/2617/cosponsors": first_page("bill_cosponsors", "cosponsors"), "/bill/119/hr/2617/committees": first_page("bill_committees", "committees"),
    "/hearing/119": first_page("hearings_list", "hearings"), "/hearing/119/senate/61880": fx("hearing_detail"),
}


# --- identity helpers -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("day,congress", [(date(2025, 1, 2), 118), (date(2025, 1, 3), 119), (date(2026, 10, 7), 119), (date(2027, 1, 2), 119),
                                          (date(2027, 1, 3), 120), (date(2023, 1, 3), 118)])
def test_congress_boundaries(day, congress):
    assert leg.congress_for(day) == congress


def test_congress_start_and_public_urls():
    assert leg.congress_start(119) == date(2025, 1, 3) and leg.congress_start(118) == date(2023, 1, 3)
    assert leg.bill_public_url(119, "hr", 2617) == "https://www.congress.gov/bill/119th-congress/house-bill/2617"
    assert leg.bill_public_url(118, "sjres", 5).endswith("118th-congress/senate-joint-resolution/5")
    assert [leg.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 112, 119)] == ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "112th", "119th"]


def test_markup_is_removed_from_summaries_without_rephrasing():
    assert leg.plain_text("<p><strong>Title</strong></p><p>This bill&nbsp;does <em>x</em> &amp; y.</p>") == "Title This bill does x & y."
    assert leg.plain_text(None) == "" and leg.plain_text("") == ""


# --- normalization --------------------------------------------------------------------------------------------

def test_bill_list_is_normalized_and_paged_request_carries_the_filter():
    p = provider(ROUTES)
    refs = list(p.list_bills(119, from_date=date(2026, 9, 28)))
    assert refs[0] == leg.BillRef(119, "hr", 2617, "Say No to Indoctrination Act", date(2026, 10, 7), date(2026, 1, 13), "Placed on the Union Calendar, Calendar No. 378.")
    assert all(r.bill_type == r.bill_type.lower() and isinstance(r.number, int) for r in refs)
    q = p.seen[0].url.params
    assert q["fromDateTime"] == "2026-09-28T00:00:00Z" and q["sort"] == "updateDate desc" and q["limit"] == "250"


def test_unusable_bill_records_are_skipped_not_guessed():
    body = {"bills": [{"congress": 119, "type": "HR", "number": "5", "title": "ok"}, {"type": "HR", "number": "6"}, {"congress": 119, "type": "XX", "number": "7"},
                      {"congress": 119, "type": "S", "number": "abc"}, "garbage", None], "pagination": {}}
    refs = list(provider({"/bill/119": body}).list_bills(119))
    assert [r.key for r in refs] == [(119, "hr", 5)] and refs[0].latest_action_date is None  # missing latest action stays None


def test_bill_detail_is_normalized_including_sponsor_policy_area_and_official_url():
    bill = provider(ROUTES).get_bill(REF)
    assert (bill.ref.title, bill.origin_chamber, bill.introduced_date, bill.policy_area) == ("Say No to Indoctrination Act", "House", date(2025, 4, 3), "Education")
    assert bill.sponsor == leg.BillSponsor("O000086", "Rep. Owens, Burgess [R-UT-4]", "R", "UT")
    assert bill.source_url == "https://www.congress.gov/bill/119th-congress/house-bill/2617"
    assert (bill.actions_count, bill.subjects_count, bill.summaries_count, bill.cosponsors_count, bill.committees_count) == (8, 3, 1, 4, 1)


def test_a_bill_without_a_sponsor_or_url_still_normalizes_and_the_url_is_reconstructed():
    body = {"bill": {"congress": 119, "type": "S", "number": "9", "title": "t", "latestAction": None, "sponsors": [], "policyArea": None}}
    bill = provider({"/bill/119/s/9": body}).get_bill(leg.BillRef(119, "s", 9))
    assert bill.sponsor is None and bill.policy_area is None and bill.introduced_date is None
    assert bill.source_url == "https://www.congress.gov/bill/119th-congress/senate-bill/9" and bill.subjects_count == 0


def test_a_bill_whose_identity_differs_from_the_request_is_rejected():
    assert provider({"/bill/119/hr/1": fx("bill_detail")}).get_bill(leg.BillRef(119, "hr", 1)) is None  # served a different bill: not trusted


def test_actions_are_normalized_and_malformed_ones_dropped():
    acts = provider(ROUTES).get_bill_actions(REF)
    assert acts[0] == leg.BillAction(date(2026, 1, 13), "Placed on the Union Calendar, Calendar No. 378.", "H12410", "Calendars")
    body = {"actions": [{"actionDate": "2026-01-01", "text": "ok"}, {"actionDate": "nope", "text": "bad date"}, {"actionDate": "2026-01-02"}, 3], "pagination": {}}
    kept = provider({"/bill/119/hr/2617/actions": body}).get_bill_actions(REF)
    assert [(a.action_date, a.code) for a in kept] == [(date(2026, 1, 1), None)]


def test_subjects_and_policy_area_are_normalized_and_deduplicated():
    area, subjects = provider(ROUTES).get_bill_subjects(REF)
    assert area == "Education" and subjects == ["Elementary and secondary education", "Sex, gender, sexual orientation discrimination"]
    body = {"subjects": {"legislativeSubjects": [{"name": "A"}, {"name": " A "}, {"name": ""}, {"name": None}, {}]}}
    assert provider({"/bill/119/hr/2617/subjects": body}).get_bill_subjects(REF) == (None, ["A"])  # trimmed, deduplicated, blanks dropped


def test_a_bill_with_no_subjects_summaries_or_committees_gives_empty_results():
    empty = {"pagination": {}}
    p = provider({"/bill/119/hr/2617/subjects": {"subjects": {}, **empty}, "/bill/119/hr/2617/summaries": {"summaries": [], **empty},
                  "/bill/119/hr/2617/committees": {"committees": [], **empty}, "/bill/119/hr/2617/cosponsors": {"pagination": {}}})
    assert p.get_bill_subjects(REF) == (None, []) and p.get_bill_summaries(REF) == [] and p.get_bill_committees(REF) == [] and p.get_bill_cosponsors(REF) == []


def test_summary_is_plain_text_with_its_official_date():
    (s,) = provider(ROUTES).get_bill_summaries(REF)
    assert s.action_date == date(2025, 4, 3) and s.description == "Introduced in House" and "<" not in s.text and s.text.startswith("Say No to Indoctrination Act This bill prohibits")


def test_cosponsors_are_normalized_including_original_and_withdrawn():
    c = provider(ROUTES).get_bill_cosponsors(REF)
    assert c[0] == leg.BillCosponsor("M001239", "Rep. McGuire, John [R-VA-5]", date(2025, 4, 3), True, None)
    body = {"cosponsors": [{"bioguideId": "A000001", "sponsorshipDate": "2025-05-01", "isOriginalCosponsor": False, "sponsorshipWithdrawnDate": "2025-06-01"}, {"fullName": "no id"}]}
    (w,) = provider({"/bill/119/hr/2617/cosponsors": body}).get_bill_cosponsors(REF)
    assert (w.original, w.withdrawn_date, w.sponsorship_date) == (False, date(2025, 6, 1), date(2025, 5, 1))


def test_committees_keep_the_official_system_code():
    (c,) = provider(ROUTES).get_bill_committees(REF)
    assert c == leg.CommitteeRef("hsed00", "Education and Workforce Committee", "House")


def test_hearings_are_listed_and_normalized_and_a_missing_committee_stays_unavailable():
    p = provider(ROUTES)
    refs = list(p.list_hearings(119))
    assert refs[0] == leg.HearingRef(119, "senate", 61880, datetime(2026, 10, 7, 14, 49, 21)) and refs[2].chamber == "house"
    h = p.get_hearing(refs[0])
    assert (h.title.startswith("RULE BY DISTRICT JUDGES"), h.citation, h.dates, h.committees, h.event_id) == (True, "S.Hrg.119-191", (date(2025, 4, 2),), (), None)
    assert h.source_url == "https://api.congress.gov/v3/hearing/119/senate/61880"


def test_hearing_with_committees_event_and_several_dates():
    body = {"hearing": {"congress": 119, "chamber": "House", "jacketNumber": 7, "title": "T", "dates": [{"date": "2025-03-05"}, {"date": "2025-03-04"}, {"date": "x"}],
                        "committees": [{"name": "Agriculture Committee", "systemCode": "hsag00"}, {"name": "no code"}], "associatedMeeting": {"eventId": 118000}}}
    h = provider({"/hearing/119/house/7": body}).get_hearing(leg.HearingRef(119, "house", 7))
    assert h.dates == (date(2025, 3, 4), date(2025, 3, 5)) and h.committees == (leg.CommitteeRef("hsag00", "Agriculture Committee"),) and h.event_id == "118000"


# --- pagination -----------------------------------------------------------------------------------------------

def test_pagination_follows_offsets_until_there_is_no_next_page():
    pages = {"0": {"bills": [{"congress": 119, "type": "HR", "number": str(n)} for n in (1, 2)], "pagination": {"next": "x"}},
             "2": {"bills": [{"congress": 119, "type": "HR", "number": "3"}], "pagination": {}}}
    p = provider({"/bill/119": lambda r: pages[r.url.params["offset"]]})
    assert [r.number for r in p.list_bills(119)] == [1, 2, 3] and [r.url.params["offset"] for r in p.seen] == ["0", "2"]


def test_a_limit_stops_paging_early():
    big = {"bills": [{"congress": 119, "type": "HR", "number": str(n)} for n in range(1, 6)], "pagination": {"next": "x"}}
    p = provider({"/bill/119": big})
    assert [r.number for r in p.list_bills(119, limit=3)] == [1, 2, 3] and len(p.seen) == 1


# --- malformed responses, retries, pacing, key handling ---------------------------------------------------------

@pytest.mark.parametrize("response", [httpx.Response(200, content=b"<html>"), httpx.Response(200, json={"bills": "not a list"}), httpx.Response(200, json=[1, 2])])
def test_malformed_responses_are_provider_errors_not_crashes(response):
    with pytest.raises((ProviderError, AttributeError)) as exc:
        list(provider({"/bill/119": response}).list_bills(119))
    assert KEY not in str(exc.value)


def test_a_missing_collection_is_an_empty_result():
    assert list(provider({"/bill/119": {"pagination": {}}}).list_bills(119)) == []


def test_not_found_means_absent_for_bills_and_hearings():
    p = provider({})
    assert p.get_bill(REF) is None and p.get_hearing(leg.HearingRef(119, "house", 1)) is None


def test_transient_errors_are_retried_with_backoff_and_retry_after_is_honoured():
    calls, sleeps = [], []

    def handler(req):
        calls.append(1)
        return httpx.Response([500, 429, 200][len(calls) - 1], headers={"Retry-After": "7"}, json={"actions": [], "pagination": {}})

    p = provider({"/actions": handler}, sleep=sleeps.append)
    assert p.get_bill_actions(REF) == [] and len(calls) == 3 and 7.0 in sleeps


def test_rate_limiting_that_never_clears_raises_the_dedicated_error():
    with pytest.raises(ProviderRateLimited):
        provider({"/actions": httpx.Response(429)}, max_retries=1).get_bill_actions(REF)


def test_the_key_is_a_header_never_in_a_url_and_a_missing_key_is_reported():
    p = provider(ROUTES)
    list(p.list_bills(119))
    assert all(r.headers["x-api-key"] == KEY and KEY not in str(r.url) for r in p.seen)
    nokey = CongressGovProvider(None, client=httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("no request without a key"))))
    with pytest.raises(NotConfigured):
        list(nokey.list_bills(119))


def test_requests_are_paced_between_pages():
    sleeps, ticks = [], iter(range(100))
    p = provider({"/bill/119": {"bills": [], "pagination": {}}, "/hearing/119": {"hearings": [], "pagination": {}}}, min_interval=0.5, sleep=sleeps.append, clock=lambda: next(ticks) * 0.1)
    list(p.list_bills(119)), list(p.list_hearings(119))
    assert sleeps and all(0 < s <= 0.5 for s in sleeps)
