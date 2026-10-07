"""Normalized legislative domain objects and the parsers that build them from Congress.gov responses.

Only this module and `congress_gov.py` know Congress.gov's field names. Parsers are tolerant: a missing or null field becomes
None, and a record that cannot be identified at all is skipped (returned as None) rather than guessed.
"""

import html
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

log = logging.getLogger(__name__)

BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}
_URL_SLUG = {
    "hr": "house-bill", "s": "senate-bill", "hjres": "house-joint-resolution", "sjres": "senate-joint-resolution",
    "hconres": "house-concurrent-resolution", "sconres": "senate-concurrent-resolution", "hres": "house-resolution",
    "sres": "senate-resolution",
}


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def bill_public_url(congress: int, bill_type: str, number: int) -> str:
    """The public Congress.gov page, reconstructable from the official identity."""
    return f"https://www.congress.gov/bill/{ordinal(congress)}-congress/{_URL_SLUG[bill_type]}/{number}"


def congress_for(day: date) -> int:
    """The Congress in session on a date. Congresses start on January 3 of odd years (the 119th began 2025-01-03)."""
    year = day.year if (day.month, day.day) >= (1, 3) else day.year - 1
    return (year - 1789) // 2 + 1


def congress_start(congress: int) -> date:
    return date(1789 + 2 * (congress - 1), 1, 3)


@dataclass(frozen=True)
class BillRef:
    congress: int
    bill_type: str  # lowercase: hr, s, hjres, ...
    number: int
    title: str | None = None
    update_date: date | None = None
    latest_action_date: date | None = None
    latest_action_text: str | None = None

    @property
    def key(self) -> tuple[int, str, int]:
        return (self.congress, self.bill_type, self.number)


@dataclass(frozen=True)
class BillSponsor:
    bioguide_id: str
    full_name: str | None = None
    party: str | None = None
    state: str | None = None


@dataclass(frozen=True)
class Bill:
    ref: BillRef
    origin_chamber: str | None = None
    introduced_date: date | None = None
    policy_area: str | None = None
    sponsor: BillSponsor | None = None
    source_url: str | None = None
    subjects_count: int = 0
    summaries_count: int = 0
    cosponsors_count: int = 0
    committees_count: int = 0
    actions_count: int = 0


@dataclass(frozen=True)
class BillAction:
    action_date: date
    text: str
    code: str | None = None
    action_type: str | None = None


@dataclass(frozen=True)
class BillSummary:
    action_date: date | None
    description: str | None
    text: str  # plain text: the markup Congress.gov returns is removed
    version_code: str | None = None
    update_date: datetime | None = None


@dataclass(frozen=True)
class BillCosponsor:
    bioguide_id: str
    full_name: str | None = None
    sponsorship_date: date | None = None
    original: bool = False
    withdrawn_date: date | None = None


@dataclass(frozen=True)
class CommitteeRef:
    code: str  # Congress.gov system code, e.g. hsed00 (a different scheme from the House Clerk's ED00)
    name: str
    chamber: str | None = None


@dataclass(frozen=True)
class HearingRef:
    congress: int
    chamber: str  # house | senate | nochamber
    jacket_number: int
    update_date: datetime | None = None


@dataclass(frozen=True)
class Hearing:
    ref: HearingRef
    title: str | None = None
    citation: str | None = None
    dates: tuple[date, ...] = ()
    committees: tuple[CommitteeRef, ...] = ()
    event_id: str | None = None
    source_url: str | None = None


class LegislationProvider(ABC):
    """An official source of legislation, legislative actions and hearings."""

    @abstractmethod
    def list_bills(self, congress: int, *, from_date: date | None = None, limit: int | None = None) -> Iterator[BillRef]: ...

    @abstractmethod
    def get_bill(self, ref: BillRef) -> Bill | None: ...

    @abstractmethod
    def get_bill_actions(self, ref: BillRef) -> list[BillAction]: ...

    @abstractmethod
    def get_bill_subjects(self, ref: BillRef) -> tuple[str | None, list[str]]:
        """(policy area, legislative subjects)."""

    @abstractmethod
    def get_bill_summaries(self, ref: BillRef) -> list[BillSummary]: ...

    @abstractmethod
    def get_bill_cosponsors(self, ref: BillRef) -> list[BillCosponsor]: ...

    @abstractmethod
    def get_bill_committees(self, ref: BillRef) -> list[CommitteeRef]: ...

    @abstractmethod
    def list_hearings(self, congress: int, *, limit: int | None = None) -> Iterator[HearingRef]: ...

    @abstractmethod
    def get_hearing(self, ref: HearingRef) -> Hearing | None: ...


# --- parsing helpers ------------------------------------------------------------------------------------------

_TAGS = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def plain_text(markup: str | None) -> str:
    """Strip the HTML in CRS summaries to readable text. Nothing is rephrased."""
    if not markup:
        return ""
    spaced = re.sub(r"</(p|li|div|h\d|tr)>|<br\s*/?>", " ", markup, flags=re.I)
    return _SPACE.sub(" ", html.unescape(_TAGS.sub("", spaced)).replace("\xa0", " ")).strip()


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        d = parse_date(value)
        return datetime(d.year, d.month, d.day) if d else None


def _count(node: Any) -> int:
    return int(node.get("count") or 0) if isinstance(node, dict) and str(node.get("count") or "0").isdigit() else 0


def _str(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def parse_bill_ref(rec: Any) -> BillRef | None:
    if not isinstance(rec, dict):
        return None
    bill_type = (_str(rec.get("type")) or "").lower()
    number = str(rec.get("number") or "")
    if bill_type not in BILL_TYPES or not number.isdigit() or not isinstance(rec.get("congress"), int):
        return None
    latest = rec.get("latestAction") if isinstance(rec.get("latestAction"), dict) else {}
    return BillRef(
        rec["congress"], bill_type, int(number), _str(rec.get("title")), parse_date(rec.get("updateDate")),
        parse_date(latest.get("actionDate")), _str(latest.get("text")),
    )


def parse_bill(rec: Any) -> Bill | None:
    ref = parse_bill_ref(rec)
    if ref is None:
        return None
    sponsors = [s for s in rec.get("sponsors") or [] if isinstance(s, dict) and _str(s.get("bioguideId"))]
    sponsor = None
    if sponsors:
        s = sponsors[0]
        sponsor = BillSponsor(s["bioguideId"].strip(), _str(s.get("fullName")), _str(s.get("party")), _str(s.get("state")))
    area = rec.get("policyArea") if isinstance(rec.get("policyArea"), dict) else {}
    return Bill(
        ref=ref, origin_chamber=_str(rec.get("originChamber")), introduced_date=parse_date(rec.get("introducedDate")),
        policy_area=_str(area.get("name")), sponsor=sponsor,
        source_url=_str(rec.get("legislationUrl")) or bill_public_url(*ref.key),
        subjects_count=_count(rec.get("subjects")), summaries_count=_count(rec.get("summaries")),
        cosponsors_count=_count(rec.get("cosponsors")), committees_count=_count(rec.get("committees")),
        actions_count=_count(rec.get("actions")),
    )


def parse_action(rec: Any) -> BillAction | None:
    if not isinstance(rec, dict):
        return None
    when, text = parse_date(rec.get("actionDate")), _str(rec.get("text"))
    return BillAction(when, text, _str(rec.get("actionCode")), _str(rec.get("type"))) if when and text else None


def parse_summary(rec: Any) -> BillSummary | None:
    if not isinstance(rec, dict):
        return None
    text = plain_text(rec.get("text") if isinstance(rec.get("text"), str) else None)
    if not text:
        return None
    return BillSummary(parse_date(rec.get("actionDate")), _str(rec.get("actionDesc")), text, _str(rec.get("versionCode")), parse_datetime(rec.get("updateDate")))


def parse_cosponsor(rec: Any) -> BillCosponsor | None:
    if not isinstance(rec, dict) or not _str(rec.get("bioguideId")):
        return None
    return BillCosponsor(
        rec["bioguideId"].strip(), _str(rec.get("fullName")), parse_date(rec.get("sponsorshipDate")),
        rec.get("isOriginalCosponsor") is True, parse_date(rec.get("sponsorshipWithdrawnDate")),
    )


def parse_committee(rec: Any) -> CommitteeRef | None:
    if not isinstance(rec, dict):
        return None
    code, name = _str(rec.get("systemCode")), _str(rec.get("name"))
    return CommitteeRef(code, name, _str(rec.get("chamber"))) if code and name else None


def parse_hearing_ref(rec: Any) -> HearingRef | None:
    if not isinstance(rec, dict):
        return None
    chamber, jacket = (_str(rec.get("chamber")) or "").lower(), rec.get("jacketNumber")
    if not chamber or not isinstance(jacket, int) or not isinstance(rec.get("congress"), int):
        return None
    return HearingRef(rec["congress"], chamber, jacket, parse_datetime(rec.get("updateDate")))


def parse_hearing(rec: Any) -> Hearing | None:
    ref = parse_hearing_ref(rec)
    if ref is None:
        return None
    dates = tuple(sorted(d for d in (parse_date(x.get("date")) for x in rec.get("dates") or [] if isinstance(x, dict)) if d))
    committees = tuple(c for c in (parse_committee(x) for x in rec.get("committees") or []) if c)
    meeting = rec.get("associatedMeeting") if isinstance(rec.get("associatedMeeting"), dict) else {}
    return Hearing(
        ref, _str(rec.get("title")), _str(rec.get("citation")), dates, committees,
        str(meeting["eventId"]) if meeting.get("eventId") else None,
        f"https://api.congress.gov/v3/hearing/{ref.congress}/{ref.chamber}/{ref.jacket_number}",
    )
