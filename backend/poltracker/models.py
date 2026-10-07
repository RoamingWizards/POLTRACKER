from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Politician(Base):
    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    chamber: Mapped[str] = mapped_column(String(10))
    party: Mapped[str | None] = mapped_column(String(20))
    state: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Official enrichment (Congress.gov / House Clerk). Only ever written for a verified, unambiguous match.
    bioguide_id: Mapped[str | None] = mapped_column(String(10), unique=True)
    district: Mapped[str | None] = mapped_column(String(20))
    official_url: Mapped[str | None] = mapped_column(String(300))
    active: Mapped[bool | None] = mapped_column(Boolean)  # in office in the most recent term the source reports
    term_start_year: Mapped[int | None] = mapped_column()  # start of the most recent term (year only: sources give no day)
    term_end_year: Mapped[int | None] = mapped_column()  # None while the term is ongoing
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime)  # last time official data was written
    enrichment_source: Mapped[str | None] = mapped_column(String(40))
    enrichment_status: Mapped[str | None] = mapped_column(String(20))  # matched | unmatched | ambiguous | conflict
    enrichment_note: Mapped[str | None] = mapped_column(String(500))  # why a politician is unresolved
    enrichment_checked_at: Mapped[datetime | None] = mapped_column(DateTime)  # last attempt, matched or not
    enrichment_method: Mapped[str | None] = mapped_column(String(40))  # how it matched: exact_name+chamber..., override

    trades: Mapped[list["Trade"]] = relationship(back_populates="politician")
    committees: Mapped[list["CommitteeAssignment"]] = relationship(
        back_populates="politician", cascade="all, delete-orphan", order_by="CommitteeAssignment.id"
    )


class PoliticianAliasOverride(Base):
    """A human-reviewed link from one POLTRACKER politician to one official Bioguide ID.

    Only ever used for a politician the deterministic matcher left unmatched. Never created automatically.
    """

    __tablename__ = "politician_alias_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(ForeignKey("politicians.id"), unique=True)
    bioguide_id: Mapped[str] = mapped_column(String(10), unique=True)
    reason: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(200))  # what the reviewer checked, e.g. a URL or record
    reviewed_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PoliticianLlmSuggestion(Base):
    """Cache and audit trail of LLM identity suggestions.

    The raw suggestion is cached so the same unresolved name is never sent twice. It is only a suggestion: every use
    re-runs the deterministic validation, and `outcome`/`reason` record the latest decision.
    """

    __tablename__ = "politician_llm_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True)
    politician_id: Mapped[int | None] = mapped_column(ForeignKey("politicians.id"), index=True)
    incoming_name: Mapped[str] = mapped_column(String(200))
    chamber: Mapped[str] = mapped_column(String(10))
    candidate_ids: Mapped[str] = mapped_column(String(2000))  # comma-separated Bioguide IDs shown to the model
    selected_bioguide_id: Mapped[str | None] = mapped_column(String(10))
    confidence: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(String(2000))
    alternates: Mapped[str | None] = mapped_column(String(500))  # comma-separated Bioguide IDs
    model: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    outcome: Mapped[str | None] = mapped_column(String(12))  # accepted | rejected
    reason: Mapped[str | None] = mapped_column(String(300))  # why it was rejected
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)


class CommitteeAssignment(Base):
    """One committee or subcommittee seat. A subcommittee row also carries its parent committee's name/code."""

    __tablename__ = "committee_assignments"
    __table_args__ = (UniqueConstraint("politician_id", "committee_code", "subcommittee_code", "source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(ForeignKey("politicians.id"), index=True)
    committee_name: Mapped[str] = mapped_column(String(300))
    committee_code: Mapped[str] = mapped_column(String(20))
    subcommittee_name: Mapped[str | None] = mapped_column(String(300))
    subcommittee_code: Mapped[str] = mapped_column(String(20), default="")  # "" = the full committee seat
    role: Mapped[str] = mapped_column(String(60), default="Member")
    chamber: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str | None] = mapped_column(String(300))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    politician: Mapped[Politician] = relationship(back_populates="committees")


class Security(Base):
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Price-cache coverage: the date range already requested from the price provider
    # (not just the range that has bars), so holidays, late IPOs and dead tickers
    # are never re-requested.
    price_from: Mapped[date | None] = mapped_column(Date)
    price_to: Mapped[date | None] = mapped_column(Date)
    price_status: Mapped[str | None] = mapped_column(String(20))  # "ok" | "unavailable"
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime)

    trades: Mapped[list["Trade"]] = relationship(back_populates="security")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    source_trade_id: Mapped[str | None] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)

    politician_id: Mapped[int] = mapped_column(ForeignKey("politicians.id"))
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"))

    politician_name: Mapped[str] = mapped_column(String(200))
    chamber: Mapped[str] = mapped_column(String(10))
    party: Mapped[str | None] = mapped_column(String(20))
    state: Mapped[str | None] = mapped_column(String(2))

    ticker: Mapped[str | None] = mapped_column(String(16))
    asset_name: Mapped[str | None] = mapped_column(String(300))
    transaction_type: Mapped[str] = mapped_column(String(20))
    transaction_date: Mapped[date] = mapped_column(Date)
    disclosure_date: Mapped[date | None] = mapped_column(Date)
    amount_min: Mapped[int | None] = mapped_column(BigInteger)
    amount_max: Mapped[int | None] = mapped_column(BigInteger)
    source_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    politician: Mapped[Politician] = relationship(back_populates="trades")
    security: Mapped[Security | None] = relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_trades_source_source_trade_id", "source", "source_trade_id"),
        Index("ix_trades_ticker", "ticker"),
        Index("ix_trades_disclosure_date", "disclosure_date"),
        Index("ix_trades_politician_id", "politician_id"),
    )


class PriceBar(Base):
    """Daily bar cache. Created now, populated in a later phase."""

    __tablename__ = "price_bars"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    adj_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(40))


class IngestState(Base):
    """Per-provider ingestion progress. `backfill_complete` flips once a run reaches the end of the
    provider's data; until then "this page is all known" must not be read as "caught up"."""

    __tablename__ = "ingest_state"

    source: Mapped[str] = mapped_column(String(40), primary_key=True)
    backfill_complete: Mapped[bool] = mapped_column(default=False)
    # When a run last finished without a provider error (even if it found nothing new).
    # Drives the stale-ingestion warning; max(trades.created_at) cannot, because quiet days add no trades.
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# --- Legislative data (official Congress.gov records). Populated by `python -m poltracker.ingest_legislation`. ----------


class Legislation(Base):
    """One bill or resolution. Identity is the official (congress, type, number), never the title."""

    __tablename__ = "legislation"
    __table_args__ = (
        UniqueConstraint("congress", "bill_type", "bill_number"),
        Index("ix_legislation_latest_action_date", "latest_action_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    congress: Mapped[int] = mapped_column()
    bill_type: Mapped[str] = mapped_column(String(10))  # hr, s, hjres, sjres, hconres, sconres, hres, sres
    bill_number: Mapped[int] = mapped_column()
    title: Mapped[str | None] = mapped_column(Text)
    origin_chamber: Mapped[str | None] = mapped_column(String(20))
    summary: Mapped[str | None] = mapped_column(Text)  # latest official CRS summary, markup removed, not rephrased
    summary_date: Mapped[date | None] = mapped_column(Date)  # the action date the summary describes
    introduced_date: Mapped[date | None] = mapped_column(Date)
    latest_action_date: Mapped[date | None] = mapped_column(Date)
    latest_action_text: Mapped[str | None] = mapped_column(Text)
    policy_area: Mapped[str | None] = mapped_column(String(200))
    sponsor_bioguide_id: Mapped[str | None] = mapped_column(String(10))  # kept even if the sponsor is not a POLTRACKER politician
    sponsor_name: Mapped[str | None] = mapped_column(String(200))
    cosponsor_count: Mapped[int | None] = mapped_column()
    source_url: Mapped[str | None] = mapped_column(String(300))  # public congress.gov page
    api_update_date: Mapped[date | None] = mapped_column(Date)  # Congress.gov's own updateDate, used to skip unchanged bills
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)  # when POLTRACKER last wrote it

    subjects: Mapped[list["LegislationSubject"]] = relationship(back_populates="legislation", cascade="all, delete-orphan")
    committees: Mapped[list["LegislationCommittee"]] = relationship(back_populates="legislation", cascade="all, delete-orphan")
    actions: Mapped[list["BillAction"]] = relationship(back_populates="legislation", cascade="all, delete-orphan", order_by="BillAction.action_date")
    politician_links: Mapped[list["PoliticianLegislation"]] = relationship(back_populates="legislation", cascade="all, delete-orphan")


class LegislationSubject(Base):
    __tablename__ = "legislation_subjects"
    __table_args__ = (UniqueConstraint("legislation_id", "subject"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"))
    subject: Mapped[str] = mapped_column(String(300))

    legislation: Mapped[Legislation] = relationship(back_populates="subjects")


class LegislationCommittee(Base):
    """A committee a bill was referred to or acted on by. `committee_code` is Congress.gov's system code (for example
    hsed00), a different scheme from the House Clerk codes in committee_assignments; mapping them is a later concern."""

    __tablename__ = "legislation_committees"
    __table_args__ = (UniqueConstraint("legislation_id", "committee_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"))
    committee_code: Mapped[str] = mapped_column(String(20))
    committee_name: Mapped[str] = mapped_column(String(300))
    chamber: Mapped[str | None] = mapped_column(String(20))

    legislation: Mapped[Legislation] = relationship(back_populates="committees")


class PoliticianLegislation(Base):
    """Sponsor / cosponsor links, only for politicians POLTRACKER already has, matched by Bioguide ID."""

    __tablename__ = "politician_legislation"
    __table_args__ = (
        UniqueConstraint("politician_id", "legislation_id", "relationship"),
        Index("ix_politician_legislation_legislation_id", "legislation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(ForeignKey("politicians.id"))
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"))
    relationship_type: Mapped[str] = mapped_column("relationship", String(20))  # sponsor | cosponsor
    sponsorship_date: Mapped[date | None] = mapped_column(Date)
    is_original: Mapped[bool | None] = mapped_column(Boolean)  # original cosponsor
    withdrawn_date: Mapped[date | None] = mapped_column(Date)  # a withdrawn cosponsor stays recorded, with the date

    legislation: Mapped[Legislation] = relationship(back_populates="politician_links")


class BillAction(Base):
    """Official legislative actions inside the ingestion window. `action_key` (hash of date, code and text) makes re-runs
    idempotent; two truly identical actions on one day collapse into one."""

    __tablename__ = "bill_actions"
    __table_args__ = (
        UniqueConstraint("legislation_id", "action_key"),
        Index("ix_bill_actions_legislation_id_action_date", "legislation_id", "action_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"))
    action_date: Mapped[date] = mapped_column(Date)
    action_text: Mapped[str] = mapped_column(Text)
    action_code: Mapped[str | None] = mapped_column(String(20))
    action_type: Mapped[str | None] = mapped_column(String(60))
    action_key: Mapped[str] = mapped_column(String(40))

    legislation: Mapped[Legislation] = relationship(back_populates="actions")


class Hearing(Base):
    """A congressional hearing record. Identity is (congress, chamber, jacket number)."""

    __tablename__ = "hearings"
    __table_args__ = (UniqueConstraint("congress", "chamber", "jacket_number"), Index("ix_hearings_hearing_date", "hearing_date"))

    id: Mapped[int] = mapped_column(primary_key=True)
    congress: Mapped[int] = mapped_column()
    chamber: Mapped[str] = mapped_column(String(20))  # house | senate | nochamber
    jacket_number: Mapped[int] = mapped_column()
    event_id: Mapped[str | None] = mapped_column(String(40))  # linked committee-meeting event, when Congress.gov has one
    title: Mapped[str | None] = mapped_column(Text)
    citation: Mapped[str | None] = mapped_column(String(60))
    hearing_date: Mapped[date | None] = mapped_column(Date)  # first date; a multi-day hearing also has hearing_end_date
    hearing_end_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(300))  # the official API record
    api_update_date: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    committees: Mapped[list["HearingCommittee"]] = relationship(back_populates="hearing", cascade="all, delete-orphan")


class HearingCommittee(Base):
    __tablename__ = "hearing_committees"
    __table_args__ = (UniqueConstraint("hearing_id", "committee_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hearing_id: Mapped[int] = mapped_column(ForeignKey("hearings.id"))
    committee_code: Mapped[str] = mapped_column(String(20))
    committee_name: Mapped[str] = mapped_column(String(300))

    hearing: Mapped[Hearing] = relationship(back_populates="committees")
