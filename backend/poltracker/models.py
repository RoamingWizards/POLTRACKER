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
