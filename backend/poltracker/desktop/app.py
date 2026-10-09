"""The one local server the packaged app runs: the React frontend at / and the existing API under /api.

127.0.0.1:<port>/        -> React single-page app (deep links such as /trades work on refresh)
127.0.0.1:<port>/api/... -> the unchanged FastAPI API, plus the desktop-only /api/refresh and /api/context/views routes
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..api.main import create_app
from ..config import Settings, get_settings
from . import paths
from .refresh import RefreshService, build_default_runners
from ..api.views import router as views_router
from .routes import router as refresh_router

log = logging.getLogger(__name__)
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]  # blocks DNS-rebinding: a web page cannot reach this server by another name


def create_desktop_app(
    *,
    frontend_dir: Path | None = None,
    settings: Settings | None = None,
    refresh: RefreshService | None = None,
    enable_refresh: bool = True,
) -> FastAPI:
    settings = settings or get_settings()
    frontend_dir = frontend_dir or paths.frontend_dist()

    api = create_app(settings)
    api.state.desktop = True  # advertised by /api/health so the frontend only asks for the desktop-only refresh status here
    api.include_router(refresh_router)
    api.include_router(views_router)  # local saved views and the last-used screen: single user, same origin
    if refresh is None and enable_refresh:
        from ..db import make_session_factory

        factory = make_session_factory()
        run_ingest, run_prices = build_default_runners(factory, settings)
        refresh = RefreshService(
            factory, interval_hours=settings.ingest_interval_hours, run_ingest=run_ingest, run_prices=run_prices
        )
    api.state.refresh = refresh
    if refresh is None:  # refresh disabled: report that honestly instead of failing
        api.state.refresh = _DisabledRefresh()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if refresh is not None:
            refresh.start()
        try:
            yield
        finally:
            if refresh is not None:
                await anyio.to_thread.run_sync(refresh.stop)

    app = FastAPI(title="POLTRACKER (desktop)", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    app.state.refresh = api.state.refresh

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/api", api)

    index = frontend_dir / "index.html"
    assets = frontend_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    root = frontend_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if not index.is_file():
            raise HTTPException(503, "The frontend build is missing. Build it with `npm run build` in frontend/.")
        candidate = (frontend_dir / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:  # e.g. favicon files; never outside the build
            return FileResponse(candidate)
        # Any other path is a client-side route: serve the app and let React Router handle it. Never cache index.html.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


class _DisabledRefresh:
    """Stand-in when automatic refresh is turned off (development/tests)."""

    def status(self) -> dict:
        return {
            "enabled": False, "running": False, "phase": "idle", "trigger": None, "label": None, "progress": None,
            "started_at": None, "finished_at": None, "last_attempt_ok": None, "last_error": None,
            "last_success_at": None, "next_run_at": None, "interval_hours": 0.0, "database_empty": False,
        }

    def trigger(self) -> tuple[bool, str]:
        return False, "Automatic refresh is disabled."
