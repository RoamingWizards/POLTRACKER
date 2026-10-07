"""Congress.gov API (v3) member roster. https://api.congress.gov/ - requires a free key.

Only this module knows Congress.gov's field names. The key is sent in the X-Api-Key header, never in the URL, so it
cannot leak through logged URLs or exception text.
"""

import logging
import re
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from .base import ProviderError, ProviderRateLimited
from .politicians import NotConfigured, OfficialMember, PoliticianProvider

log = logging.getLogger(__name__)

SOURCE = "congress.gov"
PAGE_SIZE = 250  # the API maximum

STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC", "puerto rico": "PR", "guam": "GU",
    "american samoa": "AS", "northern mariana islands": "MP", "virgin islands": "VI",
    "u.s. virgin islands": "VI",
}
PARTIES = {"democratic": "D", "republican": "R", "independent": "I", "d": "D", "r": "R", "i": "I", "id": "I"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def member_url(bioguide_id: str, first: str, last: str) -> str:
    """The public Congress.gov profile page. Built from the stable ID; the slug is cosmetic."""
    slug = re.sub(r"[^a-z0-9]+", "-", f"{first} {last}".lower()).strip("-")
    return f"https://www.congress.gov/member/{slug}/{bioguide_id}"


def _split_name(raw: str) -> tuple[str, str | None, str, str | None]:
    """'Last, First Middle, Jr.' -> (first, middle, last, suffix). Conservative: unknown shapes keep everything."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return "", None, "", None
    last = parts[0]
    suffix = None
    rest = parts[1] if len(parts) > 1 else ""
    if len(parts) > 2 and parts[2].rstrip(".").lower() in _SUFFIXES:
        suffix = parts[2]
    tokens = rest.split()
    if tokens and tokens[-1].rstrip(".").lower() in _SUFFIXES:
        suffix = tokens.pop()
    first = tokens[0] if tokens else ""
    middle = " ".join(tokens[1:]) or None
    return first, middle, last, suffix


def _terms(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("item", [])
    return [t for t in raw or [] if isinstance(t, dict)]


def _chamber(raw: str | None) -> str | None:
    text = (raw or "").lower()
    if "senate" in text:
        return "senate"
    if "house" in text:
        return "house"
    return None


def normalize_member(rec: dict[str, Any]) -> OfficialMember | None:
    """One Congress.gov member object -> OfficialMember, or None when it can't be used safely."""
    bioguide = (rec.get("bioguideId") or "").strip()
    if not bioguide:
        return None
    first, middle, last, suffix = _split_name(rec.get("name") or "")
    if not (first and last):  # fall back to the structured fields of the detail endpoint
        first = rec.get("firstName") or first
        last = rec.get("lastName") or last
        middle = rec.get("middleName") or middle
    if not (first and last):
        return None
    terms = sorted(_terms(rec.get("terms")), key=lambda t: t.get("startYear") or 0)
    latest = terms[-1] if terms else {}
    chamber = _chamber(latest.get("chamber"))
    if chamber is None:
        return None
    state_raw = (rec.get("state") or latest.get("stateName") or "").strip()
    state = state_raw.upper() if len(state_raw) == 2 else STATE_CODES.get(state_raw.lower())
    district = rec.get("district")
    if district is None:
        district = latest.get("district")
    if chamber == "house":
        district = "At Large" if district in (0, "0") else (str(district) if district is not None else None)
    else:
        district = None
    party = rec.get("partyName")
    if party is None and rec.get("partyHistory"):
        party = sorted(rec["partyHistory"], key=lambda p: p.get("startYear") or 0)[-1].get("partyName")
    party = PARTIES.get((party or "").strip().lower(), party or None)
    end_year = latest.get("endYear")
    return OfficialMember(
        bioguide_id=bioguide,
        first_name=first,
        middle_name=middle,
        last_name=last,
        suffix=suffix,
        full_name=" ".join(p for p in (first, middle, last, suffix) if p),
        chamber=chamber,
        party=party,
        state=state,
        district=district,
        active=(end_year is None) if latest else None,
        official_url=member_url(bioguide, first, last),
        term_start_year=latest.get("startYear"),
        term_end_year=end_year,
        source=SOURCE,
    )


class CongressGovProvider(PoliticianProvider):
    name = SOURCE

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://api.congress.gov/v3",
        congress: int = 119,
        min_interval: float = 0.5,
        max_retries: int = 3,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._key = (api_key or "").strip() or None
        self._congress = congress
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._sleep, self._clock = sleep, clock
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"), timeout=30)
        self._last_request = None
        self._roster: list[OfficialMember] | None = None
        self.requests_made = 0

    @property
    def configured(self) -> bool:
        return self._key is not None

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._key:
            raise NotConfigured("CONGRESS_API_KEY is not set")
        params = {"format": "json", **(params or {})}
        for attempt in range(self._max_retries + 1):
            if self._last_request is not None:  # pace every request, retries included
                wait = self._min_interval - (self._clock() - self._last_request)
                if wait > 0:
                    self._sleep(wait)
            self._last_request = self._clock()
            self.requests_made += 1
            retry_after = None
            try:
                resp = self._client.get(path, params=params, headers={"X-Api-Key": self._key, "Accept": "application/json"})
            except httpx.HTTPError as exc:
                error: ProviderError = ProviderError(f"{path}: network error ({type(exc).__name__})")
            else:
                if resp.status_code in (401, 403):
                    raise ProviderError(f"{path}: Congress.gov rejected the API key (HTTP {resp.status_code})")
                if resp.status_code == 404:
                    raise ProviderError(f"{path}: not found (HTTP 404)")
                if resp.status_code == 429:
                    error = ProviderRateLimited(f"{path}: rate limited (HTTP 429)")
                    retry_after = _retry_after(resp)
                elif resp.status_code >= 500:
                    error = ProviderError(f"{path}: server error (HTTP {resp.status_code})")
                elif resp.status_code >= 400:
                    raise ProviderError(f"{path}: HTTP {resp.status_code}")
                else:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise ProviderError(f"{path}: response was not JSON") from exc
            if attempt == self._max_retries:
                raise error
            delay = retry_after if retry_after is not None else min(2 ** (attempt + 1), 30)
            log.warning("%s; retrying in %.0fs", error, delay)
            self._sleep(delay)
        raise AssertionError("unreachable")

    def list_members(self, *, chamber: str | None = None) -> list[OfficialMember]:
        if self._roster is None:  # one roster per run: about three requests for the whole Congress
            members: dict[str, OfficialMember] = {}
            offset = 0
            while True:
                body = self._get(f"/member/congress/{self._congress}", {"limit": PAGE_SIZE, "offset": offset})
                raw = body.get("members") or []
                for rec in raw:
                    member = normalize_member(rec)
                    if member is None:
                        log.warning("Skipping unusable Congress.gov member record: %s", rec.get("bioguideId"))
                    else:
                        members[member.bioguide_id] = member
                offset += PAGE_SIZE
                if not raw or not (body.get("pagination") or {}).get("next"):
                    break
            self._roster = list(members.values())
        return [m for m in self._roster if chamber in (None, m.chamber)]

    def get_member(self, bioguide_id: str) -> OfficialMember | None:
        try:
            body = self._get(f"/member/{bioguide_id}")
        except ProviderError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        rec = body.get("member")
        if not isinstance(rec, dict):
            return None
        rec = {**rec, "bioguideId": rec.get("bioguideId") or bioguide_id}
        terms = _terms(rec.get("terms"))
        rec["terms"] = terms
        return normalize_member(rec)


def _retry_after(resp: httpx.Response) -> float | None:
    try:
        return min(float(resp.headers.get("Retry-After", "")), 120)
    except ValueError:
        return None
