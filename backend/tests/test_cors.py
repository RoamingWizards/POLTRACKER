from fastapi.testclient import TestClient

from poltracker.api.main import create_app
from poltracker.config import Settings

ALLOWED, OTHER = "https://poltracker.example", "https://evil.example"


def client(origins: str) -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, cors_origins=origins)))


def test_allowed_origin_gets_cors_headers():
    r = client(ALLOWED).get("/health", headers={"Origin": ALLOWED})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in r.headers  # no cookies are involved


def test_other_origin_gets_no_cors_headers():
    r = client(ALLOWED).get("/health", headers={"Origin": OTHER})
    assert "access-control-allow-origin" not in r.headers


def test_preflight_is_limited_to_get():
    c = client(ALLOWED)
    ok = c.options("/trades", headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET"})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == ALLOWED
    post = c.options("/trades", headers={"Origin": ALLOWED, "Access-Control-Request-Method": "POST"})
    assert post.status_code == 400  # the API is read-only; writes are never offered cross-origin


def test_several_origins_are_each_honoured():
    c = client(f"{ALLOWED}, https://staging.example")
    assert c.get("/health", headers={"Origin": "https://staging.example"}).headers["access-control-allow-origin"] == "https://staging.example"


def test_no_origins_means_no_cors_at_all():
    r = client("").get("/health", headers={"Origin": ALLOWED})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_default_app_allows_the_local_dev_server():
    r = TestClient(create_app(Settings(_env_file=None))).get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
