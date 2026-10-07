"""Where the desktop app keeps things. The writable database never lives inside POLTRACKER.app."""

import os
import sys
from pathlib import Path

HOME_ENV = "POLTRACKER_HOME"  # override for development and tests


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def support_dir() -> Path:
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "POLTRACKER"


def database_path() -> Path:
    return support_dir() / "poltracker.db"


def log_dir() -> Path:
    if os.environ.get(HOME_ENV):
        return support_dir() / "logs"
    return Path.home() / "Library" / "Logs" / "POLTRACKER"


def webview_storage_dir() -> Path:
    return support_dir() / "webview"


def lock_path() -> Path:
    return support_dir() / ".poltracker.lock"


def ensure_dirs() -> None:
    for path in (support_dir(), log_dir(), webview_storage_dir()):
        path.mkdir(parents=True, exist_ok=True)


def resource_root() -> Path:
    """The folder that holds bundled resources: PyInstaller's data root when frozen, else the repository root."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[3]


def frontend_dist() -> Path:
    return resource_root() / ("frontend_dist" if is_frozen() else "frontend/dist")


def migrations_dir() -> Path:
    return resource_root() / "migrations"
