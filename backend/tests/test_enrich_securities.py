"""Security profile enrichment: incremental, idempotent, never touches trades or ids, never breaks on missing data."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select, text

from poltracker.enrich_securities import NOT_LISTED, enrich_securities
from poltracker.models import PriceBar, Security, Trade
from poltracker.providers.base import ProviderError, ProviderRateLimited
from poltracker.providers.company_profiles import CompanyProfile, CompanyProfileProvider

NOW = datetime(2026, 10, 7, 12, 0)


def profile(ticker, sic="3721", industry="Aircraft", cik="0000936468", **kw):
    return CompanyProfile(ticker, kw.get("name", f"{ticker} CORP"), cik, sic, industry if sic else None, "Manufacturing" if sic else None, "NYSE",
                          source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")


class Fake(CompanyProfileProvider):
    name = "fake"

    def __init__(self, profiles=None, errors=None, prepare_error=None, rate_limit_after=None):
        self.profiles, self.errors, self.prepare_error, self.rate_limit_after = profiles or {}, errors or {}, prepare_error, rate_limit_after
        self.requests_made, self.calls = 0, []

    def prepare(self, tickers):
        self.requests_made += 1
        if self.prepare_error:
            raise self.prepare_error

    def get_profile(self, ticker):
        self.calls.append(ticker)
        if self.rate_limit_after is not None and len(self.calls) > self.rate_limit_after:
            raise ProviderRateLimited("429")
        if ticker in self.errors:
            raise self.errors[ticker]
        self.requests_made += 1
        return self.profiles.get(ticker)


@pytest.fixture
def secs(session_factory):
    from poltracker.models import Politician

    with session_factory() as s:
        pol = Politician(canonical_key="house:a", name="A", chamber="house")
        s.add(pol)
        s.flush()
        rows = {t: Security(ticker=t, name=f"{t} as filed") for t in ("LMT", "AAPL", "SPY", "NOSIC", "UNTRADED")}
        s.add_all(rows.values())
        s.flush()
        n = 0
        for t, sec in rows.items():
            if t == "UNTRADED":
                continue  # a security with no trades is not enriched
            n += 1
            s.add(Trade(source="t", fingerprint=f"f{n}", politician_id=pol.id, security_id=sec.id, politician_name="A", chamber="house", ticker=t,
                        transaction_type="buy", transaction_date=datetime(2026, 5, 1).date()))
        s.add(PriceBar(security_id=rows["LMT"].id, date=datetime(2026, 5, 1).date(), close=1.0, adj_close=1.0, provider="t"))
        s.commit()
        return {t: sec.id for t, sec in rows.items()}


PROFILES = {"LMT": profile("LMT"), "AAPL": profile("AAPL", "3571", "Electronic Computers", "0000320193"), "NOSIC": profile("NOSIC", sic=None, cik="0001000003")}


def get(sf, ticker):
    with sf() as s:
        return s.scalar(select(Security).where(Security.ticker == ticker))


def run(sf, provider, **kw):
    return enrich_securities(sf, provider, now=kw.pop("now", NOW), **kw)


def test_traded_securities_are_enriched_with_official_fields_and_provenance(session_factory, secs):
    r = run(session_factory, Fake(PROFILES))
    assert (r.status, r.considered, r.enriched, r.partial, len(r.unresolved)) == ("ok", 4, 2, 1, 1)
    lmt = get(session_factory, "LMT")
    assert (lmt.company_name, lmt.cik, lmt.sic_code, lmt.industry, lmt.sector, lmt.exchange) == ("LMT CORP", "0000936468", "3721", "Aircraft", "Manufacturing", "NYSE")
    assert (lmt.profile_source or "sec-edgar", lmt.profile_status, lmt.profile_checked_at, lmt.profile_updated_at) == ("sec-edgar", "ok", NOW, NOW)
    assert lmt.profile_source_url.endswith("CIK=0000936468") and lmt.name == "LMT as filed"  # the trade-derived name is left alone
    assert get(session_factory, "UNTRADED").profile_status is None  # no trades, not considered


def test_unresolved_and_partial_securities_are_recorded_with_a_reason_not_guessed(session_factory, secs):
    r = run(session_factory, Fake(PROFILES))
    spy = get(session_factory, "SPY")
    assert (spy.profile_status, spy.profile_note, spy.cik, spy.industry, spy.sector, spy.company_name) == ("unresolved", NOT_LISTED, None, None, None, None)
    nosic = get(session_factory, "NOSIC")
    assert (nosic.profile_status, nosic.cik, nosic.sic_code, nosic.industry) == ("partial", "0001000003", None, None) and "no SIC" in nosic.profile_note
    assert r.unresolved == [("SPY", NOT_LISTED)]


def test_a_second_run_is_idempotent_and_makes_no_requests(session_factory, secs):
    run(session_factory, Fake(PROFILES))
    with session_factory() as s:
        before = s.execute(text("select * from securities order by id")).all()
    again = Fake(PROFILES)
    r = run(session_factory, again, now=NOW + timedelta(days=1))
    assert (r.considered, r.skipped_current, r.skipped_recent_attempt, again.requests_made) == (0, 3, 1, 0)
    with session_factory() as s:
        assert s.execute(text("select * from securities order by id")).all() == before


def test_a_forced_rerun_rewrites_identical_values(session_factory, secs):
    run(session_factory, Fake(PROFILES))
    with session_factory() as s:
        before = [r[:-2] for r in s.execute(text("select id,ticker,name,company_name,cik,sic_code,industry,sector,exchange,profile_status,profile_note,profile_source_url from securities order by id")).all()]
    r = run(session_factory, Fake(PROFILES), force=True, now=NOW + timedelta(days=1))
    assert r.considered == 4
    with session_factory() as s:
        assert [x[:-2] for x in s.execute(text("select id,ticker,name,company_name,cik,sic_code,industry,sector,exchange,profile_status,profile_note,profile_source_url from securities order by id")).all()] == before


def test_verified_profiles_go_stale_after_the_stale_window_and_unresolved_ones_retry_sooner(session_factory, secs):
    run(session_factory, Fake(PROFILES))
    soon = Fake(PROFILES)
    r = run(session_factory, soon, now=NOW + timedelta(days=31))  # past the 30-day retry window, before the 90-day stale window
    assert r.considered == 1 and soon.calls == ["SPY"]
    later = Fake(PROFILES)
    r = run(session_factory, later, now=NOW + timedelta(days=91))
    assert r.considered == 4


def test_a_security_that_later_appears_in_the_source_gets_resolved(session_factory, secs):
    run(session_factory, Fake(PROFILES))
    r = run(session_factory, Fake({**PROFILES, "SPY": profile("SPY", "6221", "Commodity Contracts Brokers & Dealers", "0000884394")}), now=NOW + timedelta(days=31))
    assert r.enriched == 1 and get(session_factory, "SPY").profile_status == "ok" and get(session_factory, "SPY").profile_note is None


def test_a_verified_profile_is_not_wiped_if_the_source_stops_listing_the_ticker(session_factory, secs):
    run(session_factory, Fake(PROFILES))
    r = run(session_factory, Fake({k: v for k, v in PROFILES.items() if k != "LMT"}), force=True, now=NOW + timedelta(days=100))
    lmt = get(session_factory, "LMT")
    assert (lmt.profile_status, lmt.cik, lmt.industry) == ("ok", "0000936468", "Aircraft") and "earlier profile kept" in lmt.profile_note
    assert ("LMT", lmt.profile_note) in r.unresolved


def test_a_provider_error_for_one_security_leaves_it_unchecked_and_the_rest_enriched(session_factory, secs):
    r = run(session_factory, Fake(PROFILES, errors={"AAPL": ProviderError("HTTP 500")}))
    assert len(r.errors) == 1 and "AAPL" in r.errors[0] and r.enriched == 1
    assert get(session_factory, "AAPL").profile_checked_at is None  # so the next run tries again
    assert run(session_factory, Fake(PROFILES), now=NOW + timedelta(hours=1)).considered == 1


def test_an_unreachable_source_writes_nothing_and_reports_the_error(session_factory, secs):
    r = run(session_factory, Fake(prepare_error=ProviderError("network error")))
    assert r.status == "provider_error" and "network" in r.message
    with session_factory() as s:
        assert s.scalar(select(func.count(Security.id)).where(Security.profile_checked_at.is_not(None))) == 0


def test_a_rate_limit_stops_the_run_keeps_progress_and_a_rerun_continues(session_factory, secs):
    r = run(session_factory, Fake(PROFILES, rate_limit_after=1))
    assert r.status == "rate_limited" and "re-run" in r.message
    done = run(session_factory, Fake(PROFILES), now=NOW + timedelta(hours=1))
    assert done.status == "ok" and done.considered == 3  # the first one finished before the limit


def test_limit_ticker_filter_and_dry_run(session_factory, secs):
    assert run(session_factory, Fake(PROFILES), limit=2).considered == 2
    assert run(session_factory, Fake(PROFILES), tickers={"lmt"}, force=True).considered == 1
    fresh = run(session_factory, Fake(PROFILES), dry_run=True, force=True)
    assert fresh.dry_run and "nothing written" in fresh.summary()


def test_a_dry_run_leaves_a_real_sqlite_file_byte_for_byte_unchanged(tmp_path):
    import hashlib

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from poltracker.models import Base, Politician

    path = tmp_path / "real.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as s:
        pol = Politician(canonical_key="house:a", name="A", chamber="house")
        sec = Security(ticker="LMT")
        s.add_all([pol, sec])
        s.flush()
        s.add(Trade(source="t", fingerprint="f", politician_id=pol.id, security_id=sec.id, politician_name="A", chamber="house", transaction_type="buy",
                    transaction_date=datetime(2026, 5, 1).date()))
        s.commit()
    engine.dispose()
    sha = lambda: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
    before = sha()
    engine = create_engine(f"sqlite:///{path}")
    factory = sessionmaker(engine, expire_on_commit=False)
    r = enrich_securities(factory, Fake({"LMT": profile("LMT")}), now=NOW, dry_run=True)
    engine.dispose()
    assert r.enriched == 1 and sha() == before


def test_trades_security_ids_tickers_and_prices_are_untouched(session_factory, secs):
    def snap():
        with session_factory() as s:
            return [s.execute(text(q)).all() for q in ("select * from trades order by id", "select * from price_bars", "select * from politicians",
                                                        "select id, ticker, name, price_from, price_to, price_status from securities order by id")]

    before = snap()
    run(session_factory, Fake(PROFILES))
    run(session_factory, Fake(PROFILES), force=True, now=NOW + timedelta(days=100))
    assert snap() == before  # same security ids and tickers, same trade relationships, same trade-derived names


def test_no_security_is_ever_enriched_without_an_exact_source_match(session_factory, secs):
    r = run(session_factory, Fake({"LMT": profile("LMT")}))  # a source that knows only LMT
    assert r.enriched == 1 and {t for t, _ in r.unresolved} == {"AAPL", "SPY", "NOSIC"}
    assert get(session_factory, "AAPL").cik is None


# --- API serialization ----------------------------------------------------------------------------------------

def test_the_security_endpoint_serializes_profile_fields_and_nulls_for_unenriched_securities(session_factory, secs):
    from fastapi.testclient import TestClient

    from poltracker.api.main import create_app, get_session
    from poltracker.config import Settings

    run(session_factory, Fake(PROFILES))
    app = create_app(Settings(_env_file=None))

    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    client = TestClient(app)
    lmt = client.get("/securities/LMT").json()
    assert (lmt["company_name"], lmt["cik"], lmt["sic_code"], lmt["industry"], lmt["sector"], lmt["exchange"], lmt["profile_status"]) == (
        "LMT CORP", "0000936468", "3721", "Aircraft", "Manufacturing", "NYSE", "ok")
    assert lmt["profile_source_url"].startswith("https://www.sec.gov/") and lmt["name"] == "LMT as filed"
    spy = client.get("/securities/SPY").json()
    assert (spy["profile_status"], spy["cik"], spy["industry"], spy["sector"]) == ("unresolved", None, None, None)
    never = client.get("/securities/UNTRADED").json()
    assert never["profile_status"] is None and never["industry"] is None  # missing metadata is just null, never an error
