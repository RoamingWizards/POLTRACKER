"""`POLTRACKER --selftest`: drives the real window through every page and writes a JSON report, then quits."""

import json
import os
import time
from pathlib import Path

from . import paths

PAGES = ["/", "/trades", "/politicians", "/status"]


def _wait(window, expression: str, timeout: float = 20.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = window.evaluate_js(expression)
        except Exception:  # noqa: BLE001
            value = None
        if value:
            return value
        time.sleep(0.25)
    return None


def run(window, base_url: str) -> None:
    report: dict = {"url": base_url, "pages": {}}
    try:
        for page in PAGES:
            window.evaluate_js(f"window.history.pushState({{}}, '', '{page}'); window.dispatchEvent(new PopStateEvent('popstate'))")
            text = _wait(window, "document.querySelector('main') && document.querySelector('main').innerText.length > 20 ? document.querySelector('main').innerText.slice(0, 300) : ''")
            report["pages"][page] = {"rendered": bool(text), "text": (text or "")[:120]}
        report["title"] = window.evaluate_js("document.title")
        report["size"] = [window.width, window.height]
        # Detail pages: follow the first link on the list pages.
        for list_page, prefix in (("/politicians", "/politicians/"), ("/trades", "/securities/")):
            window.evaluate_js(f"window.history.pushState({{}}, '', '{list_page}'); window.dispatchEvent(new PopStateEvent('popstate'))")
            href = _wait(window, f"(document.querySelector('a[href^=\"{prefix}\"]') || {{}}).getAttribute && document.querySelector('a[href^=\"{prefix}\"]').getAttribute('href')")
            if href:
                window.evaluate_js(f"window.history.pushState({{}}, '', '{href}'); window.dispatchEvent(new PopStateEvent('popstate'))")
                text = _wait(window, "document.querySelector('main') && document.querySelector('main').innerText.length > 20 ? 'ok' : ''")
                report["pages"][href] = {"rendered": bool(text)}
        report["ok"] = all(p["rendered"] for p in report["pages"].values())
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"
    out = Path(os.environ.get("POLTRACKER_SELFTEST_OUT") or paths.support_dir() / "selftest.json")
    out.write_text(json.dumps(report, indent=2))
    window.destroy()
