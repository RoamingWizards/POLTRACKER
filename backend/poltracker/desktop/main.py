"""POLTRACKER desktop launcher: local server + native window. Also runnable as `python -m poltracker.desktop.main`."""

import fcntl
import html
import logging
import logging.handlers
import os
import sys
import time

from . import APP_NAME, paths

WINDOW_SIZE = (1400, 900)
MIN_SIZE = (900, 600)
log = logging.getLogger("poltracker.desktop")


def configure_environment() -> None:
    """Desktop defaults, set before any settings are read. Cloud DATABASE_URLs in the environment are ignored."""
    paths.ensure_dirs()
    os.chdir(paths.support_dir())  # a Finder launch has cwd "/"; also stops a stray .env elsewhere being picked up
    override = os.environ.get("POLTRACKER_DATABASE_URL")
    from .database import sqlite_url

    os.environ["DATABASE_URL"] = override or sqlite_url(paths.database_path())
    os.environ["POLTRACKER_DESKTOP"] = "1"
    os.environ.setdefault("POLTRACKER_SQLITE_WAL", "1")


def configure_logging() -> None:
    handler = logging.handlers.RotatingFileHandler(
        paths.log_dir() / "poltracker.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if not getattr(sys, "frozen", False):
        root.addHandler(logging.StreamHandler())


def acquire_lock():
    """One copy at a time: two apps writing the same SQLite file would fight over it."""
    handle = open(paths.lock_path(), "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def error_page(title: str, detail: str) -> str:
    return (
        "<body style='font:15px -apple-system,sans-serif;max-width:640px;margin:15vh auto;padding:0 24px'>"
        f"<h2>{html.escape(title)}</h2><p>{html.escape(detail)}</p>"
        f"<p style='color:#666'>Log: {html.escape(str(paths.log_dir() / 'poltracker.log'))}</p></body>"
    )


def show_error(webview, title: str, detail: str) -> int:
    log.error("%s: %s", title, detail)
    webview.create_window(APP_NAME, html=error_page(title, detail), width=720, height=420)
    webview.start()
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    selftest = "--selftest" in argv
    configure_environment()
    configure_logging()
    import webview

    lock = acquire_lock()
    if lock is None:
        return show_error(webview, "POLTRACKER is already running", "Close the other POLTRACKER window first.")

    from .database import DatabaseError, prepare_database
    from .server import LocalServer

    try:
        if "POLTRACKER_DATABASE_URL" not in os.environ:
            result = prepare_database(paths.database_path(), paths.migrations_dir())
            log.info("database ready: created=%s upgraded=%s backup=%s", result.created, result.upgraded, result.backup)
        from .app import create_desktop_app

        server = LocalServer(create_desktop_app())
        server.start()
        started = server.wait_ready()
        log.info("server ready at %s in %.2fs", server.url, started)
    except DatabaseError as exc:
        return show_error(webview, "POLTRACKER could not open its database", str(exc))
    except Exception as exc:  # noqa: BLE001
        log.exception("startup failed")
        return show_error(webview, "POLTRACKER could not start", f"{type(exc).__name__}: {exc}")

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    window = webview.create_window(APP_NAME, server.url, width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=MIN_SIZE)
    func = None
    if selftest:
        from .selftest import run as selftest_run

        func = lambda w: selftest_run(w, server.url)  # noqa: E731
    try:
        # private_mode=False + storage_path keeps the theme choice and filters between launches.
        webview.start(func, window if selftest else None, private_mode=False, storage_path=str(paths.webview_storage_dir())) if selftest \
            else webview.start(private_mode=False, storage_path=str(paths.webview_storage_dir()))
    finally:
        began = time.monotonic()
        server.stop()  # also stops the refresh service via the app lifespan
        log.info("shut down cleanly in %.2fs", time.monotonic() - began)
    return 0


if __name__ == "__main__":
    sys.exit(main())
