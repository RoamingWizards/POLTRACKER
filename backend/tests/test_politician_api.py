"""Enriched fields are exposed by the API; un-enriched politicians serialize cleanly with nulls and no committees."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import create_app, get_session
from poltracker.config import Settings
from poltracker.models import CommitteeAssignment, Politician


@pytest.fixture
def client(session_factory):
    app = create_app(Settings(_env_file=None))

    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with session_factory() as s:
        s.add_all([
            Politician(canonical_key="house:a", name="Enriched Person", chamber="house", party="D", state="TX", bioguide_id="D000399",
                       district="37", official_url="https://www.congress.gov/member/x/D000399", active=True, term_start_year=2025,
                       enriched_at=datetime(2026, 10, 7), enrichment_source="congress.gov", enrichment_status="matched", enrichment_method="override", enrichment_note="private reason text"),
            Politician(canonical_key="house:b", name="Plain Person", chamber="house"),
        ])
        s.flush()
        for name, code, sub in (("Committee on Zebras", "ZB00", None), ("Committee on Agriculture", "AG00", "Nutrition"),
                                ("Committee on Agriculture", "AG00", None)):
            s.add(CommitteeAssignment(politician_id=1, committee_name=name, committee_code=code, subcommittee_name=sub,
                                      subcommittee_code="AG03" if sub else "", role="Member", chamber="house", source="house.clerk"))
        s.commit()
    return TestClient(app)


def test_an_enriched_politician_serializes_official_fields_and_ordered_committees(client):
    body = client.get("/politicians/1").json()
    assert (body["bioguide_id"], body["district"], body["active"], body["term_start_year"], body["term_end_year"]) == (
        "D000399", "37", True, 2025, None)
    assert body["enrichment_status"] == "matched" and body["enrichment_source"] == "congress.gov"
    assert [(c["committee_name"], c["subcommittee_name"]) for c in body["committees"]] == [
        ("Committee on Agriculture", None), ("Committee on Agriculture", "Nutrition"), ("Committee on Zebras", None)]
    assert body["enrichment_method"] == "override"
    assert "enrichment_note" not in body and "private reason" not in json.dumps(body)


def test_an_unenriched_politician_has_nulls_and_no_committees(client):
    body = client.get("/politicians/2").json()
    assert body["bioguide_id"] is None and body["official_url"] is None and body["enrichment_status"] is None
    assert body["committees"] == [] and body["trade_count"] == 0


def test_the_list_endpoint_carries_the_enriched_fields_but_not_committees(client):
    items = client.get("/politicians").json()["items"]
    assert items[0]["bioguide_id"] in ("D000399", None) and all("committees" not in i for i in items)
