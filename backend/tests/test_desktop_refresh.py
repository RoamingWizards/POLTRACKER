"""The background refresh must be due-aware, polite, resilient to failure, and stoppable."""

import threading
import time
from datetime import timedelta
from types import SimpleNamespace

import pytest

from poltracker.desktop.refresh import RefreshService, utcnow
from poltracker.models import IngestState

OK = SimpleNamespace(stopped="caught up (page had nothing new)")
PRICES_OK = SimpleNamespace(failed=[], enriched=3)


class Clock:
    def __init__(self):
        self.now = utcnow()

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


def set_last_success(factory, when):
    with factory() as s:
        s.merge(IngestState(source="congressinvests", backfill_complete=True, last_success_at=when))
        s.commit()


class Recorder:
    def __init__(self, ingest=OK, prices=PRICES_OK):
        self.calls, self._ingest, self._prices = [], ingest, prices

    def run_ingest(self, on_progress, should_stop):
        self.calls.append("ingest")
        on_progress(1, 3)
        if isinstance(self._ingest, Exception):
            raise self._ingest
        return self._ingest

    def run_prices(self, on_progress, should_stop):
        self.calls.append("prices")
        on_progress(1, 2)
        if isinstance(self._prices, Exception):
            raise self._prices
        return self._prices


def make(factory, rec, clock=None, **kw):
    kw.setdefault("interval_hours", 6)
    kw.setdefault("check_every", 0.02)
    return RefreshService(factory, run_ingest=rec.run_ingest, run_prices=rec.run_prices, now=clock or utcnow, **kw)


def wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def finished(svc):
    s = svc.status()
    return not s["running"] and s["finished_at"] is not None


def test_a_first_launch_with_no_history_refreshes_immediately(session_factory):
    rec = Recorder()
    svc = make(session_factory, rec)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
    finally:
        svc.stop()
    assert rec.calls[:2] == ["ingest", "prices"]
    s = svc.status()
    assert (s["last_attempt_ok"], s["last_error"], s["phase"], s["trigger"]) == (True, None, "idle", "startup")
    assert s["database_empty"] is True


def test_a_recent_success_means_no_refresh_on_launch(session_factory):
    set_last_success(session_factory, utcnow() - timedelta(minutes=30))
    rec = Recorder()
    svc = make(session_factory, rec)
    svc.start()
    time.sleep(0.3)
    svc.stop()
    assert rec.calls == []


def test_a_stale_database_refreshes_on_launch(session_factory):
    set_last_success(session_factory, utcnow() - timedelta(hours=7))
    rec = Recorder()
    svc = make(session_factory, rec)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
    finally:
        svc.stop()
    assert rec.calls[:2] == ["ingest", "prices"]


def test_it_refreshes_again_when_the_interval_elapses_while_open(session_factory):
    clock = Clock()
    set_last_success(session_factory, clock() - timedelta(minutes=10))
    rec = Recorder()
    svc = make(session_factory, rec, clock)
    svc.start()
    time.sleep(0.2)
    assert rec.calls == []
    clock.advance(hours=6)  # six hours pass while the app stays open
    try:
        assert wait_for(lambda: len(rec.calls) >= 2)
    finally:
        svc.stop()
    assert svc.status()["trigger"] == "scheduled"


def test_a_provider_failure_is_recorded_not_raised_and_prices_still_run(session_factory):
    rec = Recorder(ingest=SimpleNamespace(stopped="provider error: /trades/recent: [Errno 8] nodename nor servname provided"))
    svc = make(session_factory, rec)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
    finally:
        svc.stop()
    s = svc.status()
    assert s["last_attempt_ok"] is False and "Congressional data" in s["last_error"] and "nodename" in s["last_error"]
    assert rec.calls[:2] == ["ingest", "prices"]  # cached prices are still refreshed independently


def test_an_unexpected_exception_does_not_kill_the_service(session_factory):
    rec = Recorder(ingest=RuntimeError("kaboom"))
    clock = Clock()
    svc = make(session_factory, rec, clock)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
        assert "kaboom" in svc.status()["last_error"]
        rec._ingest = OK  # recovers
        clock.advance(hours=7)
        assert wait_for(lambda: svc.status()["last_attempt_ok"] is True)
    finally:
        svc.stop()


def test_failures_back_off_instead_of_hammering_the_provider(session_factory):
    rec = Recorder(ingest=SimpleNamespace(stopped="provider error: offline"))
    clock = Clock()
    svc = make(session_factory, rec, clock)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
        first = rec.calls.count("ingest")
        time.sleep(0.3)  # many 20 ms checks go by, but no retry is due yet
        assert rec.calls.count("ingest") == first == 1
        clock.advance(minutes=16)  # first back-off is 15 minutes
        assert wait_for(lambda: rec.calls.count("ingest") == 2)
        time.sleep(0.2)
        clock.advance(minutes=20)  # second back-off is 30 minutes: not yet
        time.sleep(0.3)
        assert rec.calls.count("ingest") == 2
        clock.advance(minutes=15)
        assert wait_for(lambda: rec.calls.count("ingest") == 3)
    finally:
        svc.stop()


def test_a_price_provider_outage_is_reported(session_factory):
    rec = Recorder(prices=SimpleNamespace(failed=["AAPL", "MSFT"], enriched=0))
    svc = make(session_factory, rec)
    svc.start()
    try:
        assert wait_for(lambda: finished(svc))
    finally:
        svc.stop()
    assert "Market prices" in svc.status()["last_error"]


def test_the_status_reports_progress_while_running(session_factory):
    release = threading.Event()
    seen = {}

    class Slow(Recorder):
        def run_ingest(self, on_progress, should_stop):
            on_progress(4, 11)
            seen["during"] = svc.status()
            release.set()
            return OK

    rec = Slow()
    svc = make(session_factory, rec)
    svc.start()
    try:
        assert release.wait(5)
        assert wait_for(lambda: finished(svc))
    finally:
        svc.stop()
    during = seen["during"]
    assert during["running"] is True and during["phase"] == "ingesting"
    assert during["progress"] == {"done": 4, "total": 11} and during["label"]


def test_manual_refresh_is_accepted_when_idle_and_rate_limited(session_factory):
    set_last_success(session_factory, utcnow())
    rec = Recorder()
    clock = Clock()
    svc = make(session_factory, rec, clock, min_manual_gap=60)
    svc.start()
    try:
        accepted, _ = svc.trigger()
        assert accepted
        assert wait_for(lambda: finished(svc))
        accepted, reason = svc.trigger()  # immediately again
        assert not accepted and "just started" in reason
        clock.advance(seconds=61)
        assert svc.trigger()[0] is True
    finally:
        svc.stop()


def test_manual_refresh_is_refused_while_one_is_running(session_factory):
    gate, entered = threading.Event(), threading.Event()

    class Blocking(Recorder):
        def run_ingest(self, on_progress, should_stop):
            entered.set()
            gate.wait(5)
            return OK

    svc = make(session_factory, Blocking())
    svc.start()
    try:
        assert entered.wait(5)
        accepted, reason = svc.trigger()
        assert not accepted and "already running" in reason
    finally:
        gate.set()
        svc.stop()


def test_stop_interrupts_a_running_refresh_promptly(session_factory):
    started = threading.Event()

    class Interruptible(Recorder):
        def run_ingest(self, on_progress, should_stop):
            started.set()
            while not should_stop():  # like ingest_recent polling between pages
                time.sleep(0.01)
            return SimpleNamespace(stopped="stopped before finishing (the app is closing)")

    svc = make(session_factory, Interruptible())
    svc.start()
    assert started.wait(5)
    begin = time.monotonic()
    svc.stop(timeout=3)
    assert time.monotonic() - begin < 2
    assert svc._thread is not None and not svc._thread.is_alive()


def test_status_survives_a_database_error(session_factory):
    svc = make(session_factory, Recorder())

    def broken():
        raise RuntimeError("db gone")

    svc._sf = broken
    s = svc.status()  # must not raise
    assert s["enabled"] is True and s["last_success_at"] is None
