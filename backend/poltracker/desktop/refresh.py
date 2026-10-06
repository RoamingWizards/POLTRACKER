"""Keeps the local database current while the app is open.

- On launch, if the last successful ingest is older than the interval (or there never was one), refresh at once.
- While open, check once a minute whether a refresh is due (about every `interval_hours`, six by default). The due time comes
  from the database, so it survives restarts and a Mac that sleeps through a scheduled time simply refreshes on wake.
- A failed refresh (offline, provider down) never raises: it is recorded, shown on Data Status, and retried with
  exponential back-off capped at the normal interval, so the upstream APIs are never hammered.
- Everything runs on one background thread; the dashboard stays fully usable meanwhile.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..models import IngestState, Trade

log = logging.getLogger(__name__)

PHASE_IDLE, PHASE_INGEST, PHASE_PRICES = "idle", "ingesting", "prices"
LABELS = {PHASE_INGEST: "Downloading congressional trades", PHASE_PRICES: "Updating market prices"}
BACKOFF_START = timedelta(minutes=15)

IngestRunner = Callable[[Callable[[int, int | None], None], Callable[[], bool]], Any]
PriceRunner = Callable[[Callable[[int, int], None], Callable[[], bool]], Any]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # the database stores naive UTC


def iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") + "Z" if value else None


def build_default_runners(session_factory: sessionmaker[Session], settings) -> tuple[IngestRunner, PriceRunner]:
    """The real providers. Imported lazily so tests and the web app never load yfinance."""
    from ..ingest import ingest_recent
    from ..prices import refresh_prices
    from ..providers import CongressInvestsProvider
    from ..providers.prices import YFinanceProvider

    def run_ingest(on_progress, should_stop):
        provider = CongressInvestsProvider(settings.congressinvests_base_url, settings.congressinvests_api_key)
        return ingest_recent(
            provider, session_factory, page_size=settings.ingest_page_size, max_pages=settings.ingest_max_pages,
            on_progress=on_progress, should_stop=should_stop,
        )

    def run_prices(on_progress, should_stop):
        return refresh_prices(
            YFinanceProvider(), session_factory, benchmark_ticker=settings.benchmark_ticker,
            batch_size=settings.price_batch_size, retry_days=settings.price_retry_days,
            overlap_days=settings.price_tail_overlap_days, on_progress=on_progress, should_stop=should_stop,
        )

    return run_ingest, run_prices


@dataclass
class _State:
    running: bool = False
    phase: str = PHASE_IDLE
    trigger: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_ok: bool | None = None
    last_error: str | None = None
    progress: dict | None = None
    failures: int = 0
    next_attempt_at: datetime | None = None
    history: list[str] = field(default_factory=list)


class RefreshService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        interval_hours: float,
        run_ingest: IngestRunner,
        run_prices: PriceRunner,
        check_every: float = 60.0,
        min_manual_gap: float = 60.0,
        now: Callable[[], datetime] = utcnow,
    ):
        self._sf = session_factory
        self._interval = timedelta(hours=interval_hours)
        self._run_ingest, self._run_prices = run_ingest, run_prices
        self._check_every, self._min_manual_gap = check_every, timedelta(seconds=min_manual_gap)
        self._now = now
        self._state = _State()
        self._lock = threading.Lock()
        self._stop, self._wake = threading.Event(), threading.Event()
        self._manual = False
        self._thread: threading.Thread | None = None
        self._cycles = 0
        self._first_check = True

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="poltracker-refresh", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 8.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout)

    # ── public API ───────────────────────────────────────────────────────────
    def trigger(self) -> tuple[bool, str]:
        """Ask for a refresh now ("Refresh now" button). Refused while one runs or if one just started."""
        with self._lock:
            if self._state.running:
                return False, "A refresh is already running."
            if self._state.started_at and self._now() - self._state.started_at < self._min_manual_gap:
                return False, "A refresh just started; try again in a minute."
            self._manual = True
        self._wake.set()
        return True, "Refresh requested."

    def status(self) -> dict:
        last_success, empty = self._database_facts()
        with self._lock:
            s = self._state
            next_run = self._next_run_at(last_success)
            return {
                "enabled": True,
                "running": s.running,
                "phase": s.phase,
                "trigger": s.trigger,
                "label": LABELS.get(s.phase),
                "progress": dict(s.progress) if s.progress else None,
                "started_at": iso(s.started_at),
                "finished_at": iso(s.finished_at),
                "last_attempt_ok": s.last_ok,
                "last_error": s.last_error,
                "last_success_at": iso(last_success),
                "next_run_at": iso(next_run),
                "interval_hours": self._interval.total_seconds() / 3600,
                "database_empty": empty,
            }

    # ── internals ────────────────────────────────────────────────────────────
    def _database_facts(self) -> tuple[datetime | None, bool]:
        try:
            with self._sf() as session:
                last = session.scalar(select(func.max(IngestState.last_success_at)))
                empty = session.scalar(select(Trade.id).limit(1)) is None
            return last, empty
        except Exception:  # noqa: BLE001 - status must never fail the UI
            log.exception("could not read refresh facts from the database")
            return None, False

    def _next_run_at(self, last_success: datetime | None) -> datetime | None:
        due = (last_success + self._interval) if last_success else self._now()
        backoff = self._state.next_attempt_at
        return max(due, backoff) if backoff else due

    def _due_reason(self) -> str | None:
        with self._lock:
            if self._manual:
                self._manual = False
                return "manual"
            backoff = self._state.next_attempt_at
        now = self._now()
        if backoff and now < backoff:
            return None
        last_success, _ = self._database_facts()
        if last_success is None:
            return self._due_label()
        if now - last_success >= self._interval:
            return self._due_label()
        return None

    def _due_label(self) -> str:
        # "startup" only when the very first check after launch finds data due; later it is the schedule.
        return "startup" if self._first_check else "scheduled"

    def _loop(self) -> None:
        log.info("refresh service started (every %s hours)", self._interval.total_seconds() / 3600)
        while not self._stop.is_set():
            try:
                reason = self._due_reason()
                self._first_check = False
                if reason:
                    self._cycle(reason)
            except Exception:  # noqa: BLE001 - the loop must survive anything
                log.exception("unexpected error in the refresh loop")
            self._wake.wait(self._check_every)
            self._wake.clear()
        log.info("refresh service stopped")

    def _set(self, **changes) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self._state, key, value)

    def _progress(self, done: int, total: int | None) -> None:
        self._set(progress={"done": done, "total": total})

    def _cycle(self, trigger: str) -> None:
        self._cycles += 1
        log.info("refresh started (%s)", trigger)
        self._set(running=True, phase=PHASE_INGEST, trigger=trigger, started_at=self._now(), progress={"done": 0, "total": None})
        errors: list[str] = []
        ingest_failed = False

        try:
            result = self._run_ingest(self._progress, self._stop.is_set)
            stopped = getattr(result, "stopped", "") or ""
            if stopped.startswith("provider error"):
                ingest_failed = True
                errors.append("Congressional data: " + stopped.removeprefix("provider error: ")[:240])
        except Exception as exc:  # noqa: BLE001
            ingest_failed = True
            log.exception("ingestion failed")
            errors.append(f"Congressional data: {type(exc).__name__}: {str(exc)[:240]}")

        if not self._stop.is_set():
            self._set(phase=PHASE_PRICES, progress={"done": 0, "total": None})
            try:
                result = self._run_prices(self._progress, self._stop.is_set)
                if getattr(result, "failed", None) and not getattr(result, "enriched", 0):
                    errors.append(f"Market prices: the price provider did not answer ({len(result.failed)} tickers will be retried)")
            except Exception as exc:  # noqa: BLE001
                log.exception("price refresh failed")
                errors.append(f"Market prices: {type(exc).__name__}: {str(exc)[:240]}")

        finished = self._now()
        failures = (self._state.failures + 1) if ingest_failed else 0
        backoff = None
        if ingest_failed:
            backoff = finished + min(BACKOFF_START * (2 ** (failures - 1)), self._interval)
        self._set(
            running=False, phase=PHASE_IDLE, progress=None, finished_at=finished, failures=failures, next_attempt_at=backoff,
            last_ok=not errors, last_error="; ".join(errors) or None,
        )
        log.info("refresh finished: %s", "ok" if not errors else "; ".join(errors))
