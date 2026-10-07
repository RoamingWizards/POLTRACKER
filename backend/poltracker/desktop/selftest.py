"""`POLTRACKER --selftest`: drives the real window to every page, checks page-specific content, writes a JSON report, quits."""

import json
import os
import subprocess
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


def _shot(window, name: str) -> None:
    """Dev aid: POLTRACKER_SELFTEST_SHOTS=<dir> saves a screenshot of the window for each profile page."""
    out = os.environ.get("POLTRACKER_SELFTEST_SHOTS")
    if out:
        Path(out).mkdir(parents=True, exist_ok=True)
        time.sleep(1.0)
        box = f"{int(window.x)},{int(window.y)},{int(window.width)},{int(window.height)}"
        subprocess.run(["screencapture", "-x", "-R", box, str(Path(out) / f"{name}.png")], check=False)


PROFILE_JS = """(function(){
  var main = document.querySelector('main'); var card = document.querySelector('[aria-label="Official profile"]');
  if (!card) return JSON.stringify({card:false});
  var link = card.querySelector('a[href*="congress.gov"]');
  return JSON.stringify({card:true, text:card.innerText, link: link ? link.getAttribute('href') : null,
    notAvailable: card.innerText.indexOf('Not available') >= 0, items: card.querySelectorAll('li').length,
    subChips: card.querySelectorAll('.MuiChip-outlined').length, pageText: main.innerText.slice(0, 200)});
})()"""


def _profiles(window, base: str) -> dict:
    """Open real politician pages in the app: a House member, a senator, a former member, a reviewed override."""
    raw = window.evaluate_js(
        "(function(){var x=new XMLHttpRequest();x.open('GET','/api/politicians?limit=500',false);x.send();return x.responseText;})()"
    )
    items = json.loads(raw)["items"]
    counts = {"politicians": len(items), "matched": sum(1 for p in items if p.get("enrichment_status") == "matched"),
              "unresolved": sum(1 for p in items if p.get("enrichment_status") != "matched"),
              "overrides": sum(1 for p in items if p.get("enrichment_method") == "override"),
              "llm": sum(1 for p in items if p.get("enrichment_method") == "llm")}
    def pick(pred):
        return next((p for p in items if pred(p)), None)
    chosen = {
        "house_member": pick(lambda p: p["chamber"] == "house" and p.get("active") is True and p.get("enrichment_status") == "matched"),
        "senator": pick(lambda p: p["chamber"] == "senate" and p.get("active") is True and p.get("enrichment_status") == "matched"),
        "former_member": pick(lambda p: p.get("active") is False),
        "reviewed_override": pick(lambda p: p.get("enrichment_method") == "override"),
        "unenriched": pick(lambda p: p.get("enrichment_status") != "matched"),
    }
    out = {"counts": counts}
    for label, p in chosen.items():
        if p is None:
            out[label] = None
            continue
        path = f"/politicians/{p['id']}"
        window.load_url(base + path)
        time.sleep(0.5)
        ok = _wait(window, f"location.pathname === {json.dumps(path)} && document.querySelector('[aria-label=\"Official profile\"]') ? 'y' : ''")
        info = json.loads(window.evaluate_js(PROFILE_JS)) if ok else {"card": False}
        info.update({"name": p["name"], "chamber": p["chamber"], "id": p["id"], "party": p.get("party"), "state": p.get("state")})
        out[label] = info
        _shot(window, label)
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
        report["profiles"] = _profiles(window, base_url)
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["title"] = window.evaluate_js("document.title")
    report["size"] = [window.width, window.height]
    report["ok"] = "error" not in report and all(p["rendered"] for p in pages.values())
    out = Path(os.environ.get("POLTRACKER_SELFTEST_OUT") or paths.support_dir() / "selftest.json")
    out.write_text(json.dumps(report, indent=2))
    window.destroy()
