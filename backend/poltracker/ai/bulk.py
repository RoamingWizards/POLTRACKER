"""One background run that explains every canonically flagged trade that has no valid cached explanation for the chosen provider and model. At most one at a time."""

import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass
class BulkStatus:
    state: str = "idle"  # idle | running | done | failed
    provider: str | None = None
    model: str | None = None
    total: int = 0
    done: int = 0
    generated: int = 0
    cached: int = 0
    rejected: int = 0
    errors: int = 0
    message: str | None = None
    finished_at: str | None = None


class BulkJob:
    def __init__(self):
        self._lock = threading.Lock()
        self.status = BulkStatus()
        self.thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.status.state == "running"

    def snapshot(self) -> dict:
        with self._lock:
            return asdict(self.status)

    def start(self, work, *, provider: str, model: str, total: int) -> bool:
        """`work(update)` does the generation and calls `update(summary)` after each trade. False if a run is already in progress."""
        with self._lock:
            if self.status.state == "running":
                return False
            self.status = BulkStatus("running", provider, model, total)

        def update(summary):
            with self._lock:
                s = self.status
                s.done, s.generated, s.cached, s.rejected, s.errors = (summary.generated + summary.cached + summary.rejected + summary.errors + summary.over_limit,
                                                                       summary.generated, summary.cached, summary.rejected, summary.errors)

        def target():
            try:
                summary = work(update)
                with self._lock:
                    self.status.state = "failed" if summary.aborted else "done"
                    self.status.message = summary.aborted
            except Exception as exc:  # never leave the status stuck on "running"
                with self._lock:
                    self.status.state, self.status.message = "failed", f"Stopped unexpectedly ({type(exc).__name__})."
            finally:
                with self._lock:
                    self.status.finished_at = datetime.now(UTC).isoformat()

        self.thread = threading.Thread(target=target, name="ai-bulk", daemon=True)
        self.thread.start()
        return True

    def wait(self, timeout: float = 10) -> None:
        if self.thread is not None:
            self.thread.join(timeout)
