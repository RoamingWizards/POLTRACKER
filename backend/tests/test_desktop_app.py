"""The packaged app's single local server: frontend + /api, deep links, safety headers, desktop-only routes."""

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import create_app, get_session
from poltracker.config import Settings
from poltracker.desktop.app import create_desktop_app


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>POLTRACKER</title><div id=root></div>")
    (root / "assets" / "app-abc123.js").write_text("console.log('app')")
    (root / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("TOP SECRET")  # outside the build, must never be served
    return root


def client_for(dist, **kw):
    app = create_desktop_app(frontend_dir=dist, settings=Settings(_env_file=None), enable_refresh=False, **kw)
    return TestClient(app, base_url="http://127.0.0.1"), app


def test_the_root_and_client_side_routes_all_serve_the_app(dist):
    client, _ = client_for(dist)
    for route in ["/", "/trades", "/politicians", "/politicians/17", "/securities/NVDA", "/status", "/anything/deep/here"]:
        r = client.get(route)
        assert r.status_code == 200 and "<title>POLTRACKER</title>" in r.text, route
        assert r.headers["cache-control"] == "no-cache"  # a new build is picked up immediately


def test_built_assets_and_root_files_are_served(dist):
    client, _ = client_for(dist)
    assert client.get("/assets/app-abc123.js").text == "console.log('app')"
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/assets/missing.js").status_code == 404


def test_nothing_outside_the_build_can_be_read(dist):
    client, _ = client_for(dist)
    for attempt in ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt", "/..%2fsecret.txt"]:
        r = client.get(attempt)
        assert "TOP SECRET" not in r.text, attempt


def test_health_exists_at_both_levels(dist):
    client, _ = client_for(dist)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/health").json() == {"status": "ok"}


def test_the_existing_api_is_mounted_under_api(dist, session_factory):
    client, app = client_for(dist)
    inner = next(r for r in app.routes if getattr(r, "path", "") == "/api").app

    def override():
        with session_factory() as session:
            yield session

    inner.dependency_overrides[get_session] = override
    body = client.get("/api/trades").json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert client.get("/api/status").status_code == 200
    # An API path is never swallowed by the single-page-app fallback
    assert client.get("/api/no-such-route").status_code == 404


def test_other_host_names_are_rejected(dist):
    client, _ = client_for(dist)
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400  # DNS-rebinding guard
    assert client.get("/health", headers={"Host": "localhost:5173"}).status_code == 200


def test_a_missing_frontend_build_is_a_clear_error_but_the_api_still_works(tmp_path):
    client, _ = client_for(tmp_path / "nothing-here")
    r = client.get("/")
    assert r.status_code == 503 and "frontend build is missing" in r.json()["detail"]
    assert client.get("/api/health").status_code == 200


def test_refresh_routes_exist_only_in_the_desktop_app(dist):
    client, _ = client_for(dist)
    status = client.get("/api/refresh/status").json()
    assert status["enabled"] is False  # disabled here, but the route answers
    assert client.post("/api/refresh").json()["accepted"] is False
    web = TestClient(create_app(Settings(_env_file=None)))
    assert web.get("/refresh/status").status_code == 404
    assert web.post("/refresh").status_code in (404, 405)


def test_the_refresh_service_is_started_and_stopped_with_the_server(dist):
    class Fake:
        events = []

        def start(self):
            self.events.append("start")

        def stop(self, timeout=8.0):
            self.events.append("stop")

        def status(self):
            return {
                "enabled": True, "running": False, "phase": "idle", "trigger": None, "label": None, "progress": None,
                "started_at": None, "finished_at": None, "last_attempt_ok": None, "last_error": None,
                "last_success_at": None, "next_run_at": None, "interval_hours": 6.0, "database_empty": True,
            }

        def trigger(self):
            return True, "Refresh requested."

    fake = Fake()
    app = create_desktop_app(frontend_dir=dist, settings=Settings(_env_file=None), refresh=fake)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert Fake.events == ["start"]
        assert client.get("/api/refresh/status").json()["database_empty"] is True
        assert client.post("/api/refresh").json() == {"accepted": True, "reason": "Refresh requested."}
    assert Fake.events == ["start", "stop"]
