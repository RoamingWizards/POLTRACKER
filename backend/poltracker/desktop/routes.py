"""Desktop-only API routes. They are mounted only in the desktop app, never in the web API."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/refresh")


class Progress(BaseModel):
    done: int
    total: int | None = None


class RefreshStatus(BaseModel):
    enabled: bool
    running: bool
    phase: str
    trigger: str | None = None
    label: str | None = None
    progress: Progress | None = None
    started_at: str | None = None
    finished_at: str | None = None
    last_attempt_ok: bool | None = None
    last_error: str | None = None
    last_success_at: str | None = None
    next_run_at: str | None = None
    interval_hours: float
    database_empty: bool


class TriggerResult(BaseModel):
    accepted: bool
    reason: str


@router.get("/status", response_model=RefreshStatus)
def refresh_status(request: Request) -> dict:
    return request.app.state.refresh.status()


@router.post("", response_model=TriggerResult)
def refresh_now(request: Request) -> TriggerResult:
    accepted, reason = request.app.state.refresh.trigger()
    return TriggerResult(accepted=accepted, reason=reason)
