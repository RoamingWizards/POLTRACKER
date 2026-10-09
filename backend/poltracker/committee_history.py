"""Committee seat history from adopted House resolutions (official House action), checked against the Clerk's current snapshot.

The House Clerk's MemberData.xml lists the seats members hold NOW. It has no seat dates. The House elects members to standing committees by resolution
("Electing Members to certain standing committees of the House of Representatives") and removes them the same way; each adopted resolution is published by
GPO on govinfo with the date it was agreed to. Reading those gives exact start and end dates for committee seats:

  * only an ENGROSSED (`eh`) text counts, because a resolution the House never adopted (most "Removing ..." resolutions are privileged resolutions that were
    never agreed to) establishes nothing;
  * the date is the one printed on the engrossed text ("In the House of Representatives, U. S., January 6, 2025");
  * names are matched to Bioguide IDs using the Clerk roster's own formal names, and a name that could refer to more than one member is not guessed: it is set
    aside and every member it might be is marked `history_complete = False`, which stops a missing record from ever being read as "was not a member";
  * a seat with no removal stays open and is confirmed only up to the snapshot's publish date (`verified_through`), and only if the snapshot still lists it;
  * a member elected twice to a committee with no removal between is not assumed continuous: the seat counts from the later election;
  * committee level only. Subcommittee assignments are made by the committees themselves, not by House resolution, so they have no history here.

Dates are never inferred from the snapshot or from Congress boundaries. Nothing here touches the network: providers/house_resolutions.py fetches the files.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
SOURCE = "house.resolutions"
SOURCE_TYPE = "house_resolution"
PRECISION_EXACT = "exact_date"
PRECISION_CONGRESS = "congress"
PRECISION_SNAPSHOT = "current_snapshot"


def congress_of(d: date) -> int:
    """The Congress in session on a date: Congress N begins on January 3 of year 1789 + 2(N-1) (constitutional calendar, not an assignment date)."""
    year = d.year if (d.month, d.day) >= (1, 3) else d.year - 1
    return (year - 1789) // 2 + 1


# --- the Clerk roster ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class RosterMember:
    bioguide_id: str | None  # None for a member who has left (known only from a vacancy's predecessor record)
    first: str
    last: str
    official_name: str
    formal_name: str  # as the House writes it in resolutions, e.g. "Mr. Green of Texas"
    state_name: str
    sworn: date | None
    prior_congress: int = 0  # the most recent Congress the member served in before the current term (0: none); bounds who could be meant in an earlier Congress


@dataclass
class Roster:
    members: list[RosterMember]
    committees: dict[str, str]  # comcode -> full name
    snapshot_date: date | None
    congress_number: int | None
    seats: dict[tuple[str, str], bool] = field(default_factory=dict)  # (bioguide, comcode) -> on the full committee in the snapshot


def _t(node: ET.Element | None, path: str) -> str:
    found = node.find(path) if node is not None else None
    return (found.text or "").strip() if found is not None else ""


def _ymd(value: str | None) -> date | None:
    try:
        return datetime.strptime(value or "", "%Y%m%d").date()
    except ValueError:
        return None


def parse_roster(root: ET.Element) -> Roster:
    publish = root.get("publish-date") or ""
    try:
        snapshot = datetime.strptime(publish, "%B %d, %Y").date()
    except ValueError:
        snapshot = None
    cn = _t(root, "title-info/congress-num")
    committees = {c.get("comcode"): _t(c, "committee-fullname") for c in root.iter("committee") if c.get("comcode") and _t(c, "committee-fullname")}
    members: list[RosterMember] = []
    seats: dict[tuple[str, str], bool] = {}
    for node in root.iter("member"):
        info = node.find("member-info")
        state = _t(info, "state/state-fullname") if info is not None else ""
        bio = _t(info, "bioguideID")
        if bio:
            sworn = info.find("sworn-date")
            members.append(RosterMember(bio, _t(info, "firstname"), _t(info, "lastname"), _t(info, "official-name"), _t(info, "formal-name"), state,
                                        _ymd(sworn.get("date")) if sworn is not None else None, int(_t(info, "prior-congress") or 0) if _t(info, "prior-congress").isdigit() else 0))
            assignments = node.find("committee-assignments")
            for entry in (assignments if assignments is not None else []):
                if entry.tag == "committee" and entry.get("comcode"):
                    seats[(bio, entry.get("comcode"))] = True
        pred = node.find("predecessor-info")
        if pred is not None and _t(pred, "pred-lastname"):  # a member who left: kept only so that a shared surname is never guessed
            members.append(RosterMember(None, _t(pred, "pred-firstname"), _t(pred, "pred-lastname"), _t(pred, "pred-official-name"), _t(pred, "pred-formal-name"), state, None))
    return Roster(members, committees, snapshot, int(cn) if cn.isdigit() else None, seats)


# --- names ---------------------------------------------------------------------------------------------------------

_HONORIFIC = re.compile(r"^(?:Mr|Mrs|Ms|Miss|Dr)\.\s+")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z ]+", "", text.lower().replace("-", " ")).strip()


def parse_names(text: str) -> tuple[list[tuple[str, str | None]], list[str]]:
    """The names listed after a committee heading as (name, state-or-None), and any segments that could not be read as names."""
    text = re.sub(r"\([^)]*\)", "", text)
    out: list[tuple[str, str | None]] = []
    odd: list[str] = []
    for seg in (s.strip(" .") for s in text.split(",")):
        if not seg or re.match(r"(?:Vice )?Chair\b|Ranking Member\b|to rank\b", seg):
            continue
        seg = re.split(r"\s+to rank\b", seg)[0].strip()
        m = _HONORIFIC.match(seg)
        if not m:
            odd.append(seg)
            continue
        rest = seg[m.end():].strip()
        state = None
        if " of " in rest:
            rest, state = rest.rsplit(" of ", 1)
        out.append((rest.strip(), state.strip() if state else None))
    return out, odd


def candidates(name: str, state: str | None, roster: list[RosterMember], on: date, current_congress: int | None = None) -> list[RosterMember]:
    """Roster members (current or departed) the House's wording could refer to on a date. In the roster's own Congress a member is not a candidate before being sworn
    in; in an earlier Congress only a member who served then (prior_congress at least that Congress) is. Departed members are always candidates, so a shared
    surname is set aside rather than guessed."""
    n_congress = congress_of(on)
    n = _norm(name)
    words = n.split()
    found = []
    for m in roster:
        last = _norm(m.last)
        if not last or not (words and (words[-1] == last.split()[-1] or n == last)):
            continue
        full_words = set(_norm(f"{m.first} {m.official_name}").split())
        if len(words) > len(last.split()) and not set(words[: -len(last.split())]) <= full_words:
            continue  # a first name was given and it is not this member's
        if state and _norm(state) != _norm(m.state_name):
            continue
        if m.bioguide_id:
            if current_congress is None or n_congress == current_congress:
                if m.sworn and on < m.sworn:
                    continue
            elif n_congress < current_congress and m.prior_congress < n_congress:
                continue
        found.append(m)
    return found


# --- resolutions ---------------------------------------------------------------------------------------------------

@dataclass
class Event:
    date: date
    resolution: str  # "H.Res. 38"
    url: str
    verb: str  # elected | removed
    committee_code: str
    bioguide_id: str


@dataclass
class ParseReport:
    resolutions: int = 0
    events: int = 0
    unresolved_names: int = 0  # no roster member could be meant (usually someone who has left)
    ambiguous_names: int = 0
    unmapped_committees: set[str] = field(default_factory=set)
    odd_segments: list[str] = field(default_factory=list)
    ambiguous_members: set[str] = field(default_factory=set)  # members a set-aside name might have been
    notes: list[str] = field(default_factory=list)


def parse_resolution(xml: bytes | str) -> dict | None:
    """The adoption date and committee paragraphs of an engrossed committee-election/removal resolution, or None for any other document."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    body = root.find("resolution-body")
    if body is None:
        return None
    plain = re.sub(r"\s+", " ", " ".join(root.itertext()))
    m = re.search(rf"In the House of Representatives, U\. ?S\.,\s+({MONTHS}) (\d{{1,2}}), (\d{{4}})", plain)
    if not m:
        return None
    opening = " ".join(" ".join(e.itertext()) for e in body.iter("text") if e.text is not None and "committee" in (e.text or "").lower())[:400].lower()
    verb = "elected" if "elected" in opening else "removed" if "removed" in opening else "ranked" if "ranked" in opening else None
    # The House marks a committee and its members either as <committee-appointment-paragraph> or as a numbered <paragraph>: both hold a header and a text.
    paragraphs = [(re.sub(r"\s+", " ", "".join(p.find("header").itertext())).strip(" :"), re.sub(r"\s+", " ", "".join(p.find("text").itertext())).strip())
                  for p in body.iter() if p.find("header") is not None and p.find("text") is not None]
    return {"date": datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date(), "verb": verb, "paragraphs": paragraphs}


def committee_code(header: str, committees: dict[str, str]) -> str | None:
    h = _norm(header.replace("’", "'").replace("Committee on ", "").replace("the ", ""))
    for code, name in committees.items():
        if _norm(name.replace("Committee on ", "").replace("the ", "")) == h:
            return code
    return None


def build_events(documents: list[tuple[str, str, bytes | str]], roster: Roster) -> tuple[list[Event], ParseReport]:
    """documents: (resolution label, url, engrossed XML). Names that cannot be placed are reported, never guessed."""
    report = ParseReport()
    events: list[Event] = []
    for label, url, xml in documents:
        doc = parse_resolution(xml)
        if doc is None or doc["verb"] not in ("elected", "removed"):
            continue
        report.resolutions += 1
        for header, text in doc["paragraphs"]:
            code = committee_code(header, roster.committees)
            if code is None:
                report.unmapped_committees.add(header)
                continue
            names, odd = parse_names(text)
            report.odd_segments += [f"{label}: {o}" for o in odd]
            for name, state in names:
                found = candidates(name, state, roster.members, doc["date"], roster.congress_number)
                if len(found) == 1 and found[0].bioguide_id:
                    events.append(Event(doc["date"], label, url, doc["verb"], code, found[0].bioguide_id))
                    report.events += 1
                elif len(found) > 1:
                    report.ambiguous_names += 1
                    report.ambiguous_members |= {m.bioguide_id for m in found if m.bioguide_id}
                else:
                    report.unresolved_names += 1
    return events, report


# --- intervals -----------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Interval:
    bioguide_id: str
    committee_code: str
    congress: int
    start: date
    end: date | None
    verified_through: date | None  # for an open interval: the snapshot date, only if the snapshot still lists the seat
    url: str
    history_complete: bool
    note: str | None = None


def build_intervals(events: list[Event], roster: Roster, ambiguous: set[str]) -> list[Interval]:
    out: list[Interval] = []
    by_key: dict[tuple[str, str, int], list[Event]] = {}
    for e in events:
        by_key.setdefault((e.bioguide_id, e.committee_code, congress_of(e.date)), []).append(e)
    for (bio, code, congress), evs in by_key.items():
        evs.sort(key=lambda e: (e.date, e.verb == "removed"))  # an election and a removal on the same day: the election first
        complete = bio not in ambiguous
        notes: list[str] = []
        pending: tuple[Event] | None = None
        spans: list[tuple[date, date | None, str]] = []
        for e in evs:
            if e.verb == "elected":
                if pending is not None:  # elected again without a removal: continuity is not established, count from the later election
                    complete = False
                    notes.append(f"elected again on {e.date} without a removal; earlier continuity not established")
                pending = e
            elif pending is not None:
                spans.append((pending.date, e.date, pending.url))
                pending = None
            else:  # a removal with no election on record
                complete = False
                notes.append(f"removed on {e.date} with no election on record")
        if pending is not None:
            spans.append((pending.date, None, pending.url))
        for start, end, url in spans:
            through = None
            if end is None and congress == roster.congress_number and roster.seats.get((bio, code)) and roster.snapshot_date:
                through = roster.snapshot_date  # still listed on the full committee in the snapshot
            out.append(Interval(bio, code, congress, start, end, through, url, complete, "; ".join(notes) or None))
    return out
