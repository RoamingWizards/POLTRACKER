"""Office of the Clerk of the U.S. House: official member roster and committee assignments.

One public XML file (no key needed): https://clerk.house.gov/xml/lists/MemberData.xml
It lists every sitting Representative with their Bioguide ID, and each member's committee and subcommittee seats.
This module is both a PoliticianProvider (House members only) and the House CommitteeProvider.

The Senate publishes its committee membership at senate.gov, which refuses automated clients (HTTP 403 from
Akamai), so Senate committees are not available from here; see docs/POLITICIAN_ENRICHMENT.md.
"""

import logging
import re
import xml.etree.ElementTree as ET

import httpx

from .base import ProviderError
from .congress_gov import member_url
from .politicians import CommitteeProvider, CommitteeSeat, OfficialMember, PoliticianProvider

log = logging.getLogger(__name__)

SOURCE = "house.clerk"
URL = "https://clerk.house.gov/xml/lists/MemberData.xml"
_PARTIES = {"D": "D", "R": "R", "I": "I", "ID": "I"}


def _text(node: ET.Element | None, path: str) -> str | None:
    found = node.find(path) if node is not None else None
    value = (found.text or "").strip() if found is not None else ""
    return value or None


def _district(raw: str | None) -> str | None:
    if raw is None:
        return None
    digits = re.match(r"(\d+)", raw)
    return digits.group(1) if digits else raw  # "1st" -> "1"; "At Large" stays as published


def parse_members(root: ET.Element) -> list[OfficialMember]:
    members = []
    for node in root.iter("member"):
        info = node.find("member-info")
        bioguide = _text(info, "bioguideID")
        first, last = _text(info, "firstname"), _text(info, "lastname")
        if info is None or not (bioguide and first and last):  # vacant seats have no Bioguide ID
            continue
        state = info.find("state")
        sworn = info.find("sworn-date")
        year = None
        if sworn is not None and re.match(r"\d{4}", sworn.get("date", "")):
            year = int(sworn.get("date")[:4])
        party = _text(info, "party")
        middle, suffix = _text(info, "middlename"), _text(info, "suffix")
        members.append(
            OfficialMember(
                bioguide_id=bioguide,
                first_name=first,
                middle_name=middle,
                last_name=last,
                suffix=suffix,
                full_name=_text(info, "official-name") or " ".join(p for p in (first, middle, last, suffix) if p),
                chamber="house",
                party=_PARTIES.get(party or "", party),
                state=state.get("postal-code") if state is not None else None,
                district=_district(_text(info, "district")),
                active=True,  # the Clerk lists sitting members only
                official_url=member_url(bioguide, first, last),
                term_start_year=year,
                source=SOURCE,
            )
        )
    return members


def parse_committees(root: ET.Element, source_url: str = URL) -> dict[str, list[CommitteeSeat]]:
    names: dict[str, str] = {}  # committee code -> name
    subs: dict[str, tuple[str, str]] = {}  # subcommittee code -> (parent code, name)
    for committee in root.iter("committee"):
        code = committee.get("comcode")
        full = _text(committee, "committee-fullname")
        if code and full:
            names[code] = full
            for sub in committee.findall("subcommittee"):
                sub_name = _text(sub, "subcommittee-fullname")
                if sub.get("subcomcode") and sub_name:
                    subs[sub.get("subcomcode")] = (code, sub_name)

    seats: dict[str, list[CommitteeSeat]] = {}
    for node in root.iter("member"):
        bioguide = _text(node.find("member-info"), "bioguideID")
        assignments = node.find("committee-assignments")
        if not bioguide or assignments is None:
            continue
        for entry in assignments:
            role = entry.get("leadership") or "Member"
            if entry.tag == "committee" and entry.get("comcode") in names:
                code = entry.get("comcode")
                seat = CommitteeSeat(bioguide, names[code], code, "house", role=role, source=SOURCE, source_url=source_url)
            elif entry.tag == "subcommittee" and entry.get("subcomcode") in subs:
                sub_code = entry.get("subcomcode")
                parent, sub_name = subs[sub_code]
                seat = CommitteeSeat(
                    bioguide, names[parent], parent, "house", sub_name, sub_code, role, source=SOURCE, source_url=source_url
                )
            else:
                log.warning("Unknown committee entry %s for %s", entry.attrib, bioguide)
                continue
            seats.setdefault(bioguide, []).append(seat)
    return seats


class HouseClerkProvider(PoliticianProvider, CommitteeProvider):
    name = SOURCE
    chambers = ("house",)

    def __init__(self, client: httpx.Client | None = None, url: str = URL):
        self._client = client or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "POLTRACKER/0.1"})
        self._url = url
        self._root: ET.Element | None = None
        self.requests_made = 0

    def _load(self) -> ET.Element:
        if self._root is None:  # one download per run
            self.requests_made += 1
            try:
                resp = self._client.get(self._url)
            except httpx.HTTPError as exc:
                raise ProviderError(f"House Clerk member data: network error ({type(exc).__name__})") from exc
            if resp.status_code != 200:
                raise ProviderError(f"House Clerk member data: HTTP {resp.status_code}")
            try:
                self._root = ET.fromstring(resp.content)
            except ET.ParseError as exc:
                raise ProviderError("House Clerk member data: response was not valid XML") from exc
        return self._root

    def list_members(self, *, chamber: str | None = None) -> list[OfficialMember]:
        return [] if chamber == "senate" else parse_members(self._load())

    def get_member(self, bioguide_id: str) -> OfficialMember | None:
        return next((m for m in self.list_members() if m.bioguide_id == bioguide_id), None)

    def get_committees(self, bioguide_ids: set[str] | None = None) -> dict[str, list[CommitteeSeat]]:
        seats = parse_committees(self._load(), self._url)
        return seats if bioguide_ids is None else {k: v for k, v in seats.items() if k in bioguide_ids}
