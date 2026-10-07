"""Conservative matching of a POLTRACKER politician to an official roster entry.

A match needs ALL of: same chamber, the same normalized name, and (when POLTRACKER knows it) the same state. It
must also be the only such member. Anything weaker is left unmatched and recorded, never guessed:
nicknames ("Dan" vs "Daniel"), different spellings and shared surnames are not matched.

Name normalization (no guessing): accents folded, case/punctuation ignored, honorifics and generational suffixes
dropped, single-letter middle initials ignored. A full middle name must agree when both sides have one; a politician
recorded without a middle name matches an official entry that has one.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from .normalize import normalize_name
from .providers.politicians import OfficialMember

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    folded = re.sub(r"['’`.]", "", folded.lower())  # O'Halleran -> ohalleran, J. -> j
    return [t for t in re.split(r"[^a-z0-9]+", folded) if t]


def _drop_suffix(tokens: list[str]) -> list[str]:
    return tokens[:-1] if len(tokens) > 2 and tokens[-1] in _SUFFIXES else tokens


@dataclass(frozen=True)
class _Name:
    first_to_last: tuple[str, ...]  # tokens without middle initials
    initials: tuple[str, ...]  # single-letter middle tokens that were dropped

    @classmethod
    def of_politician(cls, name: str) -> "_Name":
        tokens = _drop_suffix(_tokens(normalize_name(name)))
        kept, initials = [], []
        for i, t in enumerate(tokens):
            if 0 < i < len(tokens) - 1 and len(t) == 1:
                initials.append(t)
            else:
                kept.append(t)
        return cls(tuple(kept), tuple(initials))


def _official_variants(m: OfficialMember) -> list[tuple[tuple[str, ...], str | None]]:
    """(token sequence, full middle) for the spellings an official entry can be matched under."""
    first, last = _tokens(m.first_name), _tokens(m.last_name)
    middle = [t for t in _tokens(m.middle_name or "")]
    middle_full = [t for t in middle if len(t) > 1]
    variants = [(tuple(first + middle_full + last), " ".join(middle_full) or None)]
    if middle_full:
        variants.append((tuple(first + last), None))
    for alias in m.aliases:  # spellings the official source itself publishes
        variants.append((tuple(_drop_suffix(_tokens(alias))), None))
    return variants


def _name_matches(pol: _Name, m: OfficialMember) -> bool:
    middle_initial = (_tokens(m.middle_name or "") or [""])[0][:1]
    if pol.initials and middle_initial and pol.initials[0] != middle_initial:
        return False  # "David Q. Taylor" is not "David J. Taylor"
    return any(pol.first_to_last == seq for seq, _mid in _official_variants(m))


def _extra_middle_matches(pol: _Name, m: OfficialMember) -> bool:
    """Same first and last name, plus middle name(s) POLTRACKER has and the official entry omits or only abbreviates.

    'Kelly Louise Morrison' ~ 'Kelly Morrison'; 'Carol Devine Miller' ~ 'Carol D. Miller'. Never used when the
    official entry carries a different middle name, and never for a different first name or spelling.
    """
    seq = pol.first_to_last
    first, last = _tokens(m.first_name), _tokens(m.last_name)
    if len(seq) <= len(first) + len(last) or list(seq[: len(first)]) != first or list(seq[-len(last):]) != last:
        return False
    middle = list(seq[len(first) : len(seq) - len(last)])
    official_middle = _tokens(m.middle_name or "")
    if not official_middle:
        return True
    om = official_middle[0]
    return len(om) == 1 and middle[0].startswith(om) or middle == official_middle


@dataclass
class MatchResult:
    status: str  # matched | ambiguous | unmatched
    member: OfficialMember | None = None
    rule: str | None = None
    candidates: list[OfficialMember] = field(default_factory=list)
    note: str | None = None


def _find(name, members, chamber, state) -> tuple[list[OfficialMember], str]:
    pol = _Name.of_politician(name)
    pool = [
        m for m in members
        if (not chamber or m.chamber == chamber) and not (state and m.state and m.state != state.upper())
    ]
    strict = [m for m in pool if _name_matches(pol, m)]
    if strict:
        return strict, "exact_name"
    return [m for m in pool if _extra_middle_matches(pol, m)], "name_with_extra_middle"


def candidates(
    name: str, members: list[OfficialMember], *, chamber: str | None = None, state: str | None = None
) -> list[OfficialMember]:
    return _find(name, members, chamber, state)[0]


def match_politician(name: str, chamber: str, state: str | None, members: list[OfficialMember]) -> MatchResult:
    found, rule = _find(name, members, chamber, state)
    if len(found) == 1:
        # The label is stable: it must not change once a state has been filled in.
        return MatchResult("matched", found[0], f"{rule}+chamber", found)
    if len(found) > 1:
        who = ", ".join(f"{m.full_name} ({m.state}, {m.bioguide_id})" for m in found[:5])
        return MatchResult("ambiguous", None, None, found, f"{len(found)} officials share this name in the {chamber}: {who}")
    # Unmatched: say who is close, for a human to review. Nothing is assigned.
    pol = _Name.of_politician(name)
    surname = pol.first_to_last[-1] if pol.first_to_last else ""
    near = [m for m in members if m.chamber == chamber and surname and _tokens(m.last_name)[-1:] == [surname]]
    note = "no official member with this name in the " + chamber
    if near:
        note += "; same surname: " + ", ".join(f"{m.full_name} ({m.state}, {m.bioguide_id})" for m in near[:4])
    return MatchResult("unmatched", None, None, near, note[:500])
