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

    # Company profile (Phase 1 of committee/sector context). Official identifiers and classification from SEC EDGAR; never
    # inferred, never from a language model. `name` above stays the name as it appeared in trades.
    company_name: Mapped[str | None] = mapped_column(String(300))
    cik: Mapped[str | None] = mapped_column(String(10))  # SEC Central Index Key, zero-padded
    sic_code: Mapped[str | None] = mapped_column(String(4))  # Standard Industrial Classification code
    industry: Mapped[str | None] = mapped_column(String(200))  # the official SIC description, as published
    sector: Mapped[str | None] = mapped_column(String(100))  # the official SIC division derived from the SIC code
    exchange: Mapped[str | None] = mapped_column(String(40))
    profile_source: Mapped[str | None] = mapped_column(String(40))  # sec-edgar
    profile_source_url: Mapped[str | None] = mapped_column(String(300))
    profile_status: Mapped[str | None] = mapped_column(String(20))  # ok | partial (no SIC) | unresolved (not in the source)
    profile_note: Mapped[str | None] = mapped_column(String(300))
    profile_checked_at: Mapped[datetime | None] = mapped_column(DateTime)  # last attempt, whatever the outcome
    profile_updated_at: Mapped[datetime | None] = mapped_column(DateTime)  # last time profile fields were written

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


class CommitteeIndustryMapping(Base):
    """A reviewed, deterministic link from a committee/subcommittee's official jurisdiction to a range of SIC codes.

    Used only to say whether a company's industry is within an area plausibly relevant to a committee's jurisdiction. It is context,
    not evidence of anything. Rows are authored from the official jurisdiction text and carry their citation and rationale.
    `relevance_level` is direct, related, or none (the committee was reviewed and has no industry-specific jurisdiction, in which case
    the SIC range is empty). A subcommittee row (subcommittee_code set) is more specific than its parent committee's rows.
    """

    __tablename__ = "committee_industry_mappings"
    __table_args__ = (Index("ix_committee_industry_mappings_version_committee", "mapping_version", "committee_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chamber: Mapped[str] = mapped_column(String(10))
    committee_code: Mapped[str] = mapped_column(String(20))  # the House Clerk code used by committee_assignments (e.g. AS00)
    subcommittee_code: Mapped[str | None] = mapped_column(String(20))
    committee_name: Mapped[str] = mapped_column(String(300))
    subcommittee_name: Mapped[str | None] = mapped_column(String(300))
    sic_start: Mapped[int | None] = mapped_column()  # inclusive; null only for relevance_level 'none'
    sic_end: Mapped[int | None] = mapped_column()
    industry_pattern: Mapped[str | None] = mapped_column(String(200))  # optional regex that must also match the SIC description
    relevance_level: Mapped[str] = mapped_column(String(10))  # direct | related | none
    rationale: Mapped[str] = mapped_column(Text)
    jurisdiction_text: Mapped[str | None] = mapped_column(Text)  # the official text relied on
    source_citation: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(300))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)  # null until a person has reviewed the mapping
    # Human review state. `reviewed` requires reviewed_at (and ideally reviewed_by); every row starts as needs_review and stays that way until
    # a person explicitly approves it.
    review_status: Mapped[str] = mapped_column(String(15), default="needs_review", server_default="needs_review")  # needs_review | reviewed
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    review_note: Mapped[str | None] = mapped_column(Text)  # reviewer comments, or the history of an earlier correction
    # How the jurisdiction was established: rule_x_text (the Rule X wording was read), committee_published_text (the committee's own subcommittee
    # text was read), subcommittee_name (inferred from the subcommittee's official name), committee_name (inferred from the committee's name only).
    jurisdiction_basis: Mapped[str | None] = mapped_column(String(30))
    mapping_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
