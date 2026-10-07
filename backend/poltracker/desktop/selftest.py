"""`POLTRACKER --selftest`: drives the real window to every page, checks page-specific content, writes a JSON report, quits."""

import json
import os
import time
from pathlib import Path

from . import paths

MAIN = "(document.querySelector('main')||{}).innerText||''"


def _wait(window, expression: str, timeout: float = 25.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = window.evaluate_js(expression)
        except Exception:  # noqa: BLE001
            value = None
        if value:
            return value
        time.sleep(0.4)
    return None


def _visit(window, base: str, path: str, expect: str, charts: bool = False) -> dict:
    window.load_url(base + path)
    time.sleep(0.5)
    ok = _wait(window, f"location.pathname === {json.dumps(path)} && ({MAIN}).includes({json.dumps(expect)}) ? 'y' : ''")
    out = {"rendered": bool(ok)}
    if charts:
        out["svg_charts"] = _wait(window, "document.querySelectorAll('main svg.MuiChartsSurface-root, main svg[class*=Charts]').length || ''") or 0
        out["rendered"] = out["rendered"] and bool(out["svg_charts"])
    return out


def run(window, base_url: str) -> None:
    report: dict = {"url": base_url, "pages": {}}
    pages = report["pages"]
    try:
        pages["/"] = _visit(window, base_url, "/", "Trades stored", charts=True)
        pages["/trades"] = _visit(window, base_url, "/trades", "Trades")
        pages["/politicians"] = _visit(window, base_url, "/politicians", "Politicians")
        pages["/status"] = _visit(window, base_url, "/status", "Background refresh")
        # Detail pages: real ids from the app's own API (synchronous XHR so evaluate_js returns the value).
        ids = window.evaluate_js(
            "(function(){var x=new XMLHttpRequest();x.open('GET','/api/trades?limit=1',false);x.send();"
            "var t=JSON.parse(x.responseText).items[0];return t.politician_id+'|'+t.ticker;})()"
        )
        pol, ticker = ids.split("|")
        pages[f"/politicians/{pol}"] = _visit(window, base_url, f"/politicians/{pol}", "Trades", charts=False)
        pages[f"/securities/{ticker}"] = _visit(window, base_url, f"/securities/{ticker}", ticker, charts=True)
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["title"] = window.evaluate_js("document.title")
    report["size"] = [window.width, window.height]
    report["ok"] = "error" not in report and all(p["rendered"] for p in pages.values())
    out = Path(os.environ.get("POLTRACKER_SELFTEST_OUT") or paths.support_dir() / "selftest.json")
    out.write_text(json.dumps(report, indent=2))
    window.destroy()
