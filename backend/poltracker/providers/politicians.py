"""Provider interfaces for official politician metadata and committee membership.

Implementations own every source-specific field name. The rest of the application only sees the domain
objects defined here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from .base import ProviderError


class NotConfigured(ProviderError):
    """The provider needs credentials/settings that are absent. Callers report this instead of failing."""


@dataclass(frozen=True)
class OfficialMember:
    bioguide_id: str
    first_name: str
    last_name: str
    chamber: str  # "house" | "senate"
    middle_name: str | None = None
    suffix: str | None = None
    full_name: str = ""
    nickname: str | None = None
    party: str | None = None  # "D" | "R" | "I", or the source's own word if it is none of those
    state: str | None = None  # two-letter postal code
    district: str | None = None  # house only; "At Large" for single-district states and delegates
    active: bool | None = None
    official_url: str | None = None
    term_start_year: int | None = None
    term_end_year: int | None = None  # None while the term is ongoing
    source: str = ""
    # Other spellings the source itself publishes for this person (for example "Mike" and "Michael").
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CommitteeSeat:
    bioguide_id: str
    committee_name: str
    committee_code: str
    chamber: str
    subcommittee_name: str | None = None
    subcommittee_code: str = ""  # "" = a seat on the full committee
    role: str = "Member"
    start_date: date | None = None
    end_date: date | None = None
    source: str = ""
    source_url: str | None = None
    # Temporal provenance (see CommitteeAssignment): a snapshot seat is only known to exist on the snapshot's publish date.
    congress_number: int | None = None
    temporal_precision: str | None = None
    source_type: str | None = None
    verified_through: date | None = None


class PoliticianProvider(ABC):
    """An official roster of members of Congress."""

    name: str

    @abstractmethod
    def list_members(self, *, chamber: str | None = None) -> list[OfficialMember]:
        """Every member the source knows for the configured Congress."""

    @abstractmethod
    def get_member(self, bioguide_id: str) -> OfficialMember | None:
        """One member by stable Bioguide ID, or None if the source does not know it."""

    def search_member(self, name: str, *, chamber: str | None = None, state: str | None = None) -> list[OfficialMember]:
        """Candidate members for a name. Candidates only: choosing among them is the matcher's job."""
        from ..politician_match import candidates

        return candidates(name, self.list_members(chamber=chamber), chamber=chamber, state=state)


class CommitteeProvider(ABC):
    """An official source of committee and subcommittee membership."""

    name: str
    chambers: tuple[str, ...]

    @abstractmethod
    def get_committees(self, bioguide_ids: set[str] | None = None) -> dict[str, list[CommitteeSeat]]:
        """Seats keyed by Bioguide ID (only the requested IDs when given)."""
