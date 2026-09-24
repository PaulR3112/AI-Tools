import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.ingestion import pipeline
from app.main import app
from app.models import ApiAuditEvent, Offer

DAY = "2026-09-24"  # v platnosti testovacieho letáku 23.–29. 9.
ADMIN = {"Authorization": "Bearer test-admin-token"}


@pytest.fixture
def client(session, source, deps):
    pipeline.check_source(session, source.id, deps)
    return TestClient(app)


def names(resp):
    assert resp.status_code == 200, resp.text
    return [o["raw_name"] for o in resp.json()["items"]]


def test_search_tvaroh_returns_active_offers_sorted_by_unit_price(client):
    r = client.get("/v1/offers/search", params={"q": "tvaroh", "active_at": DAY})
    # „Tvaroh tučný“ je v review → nie je vo výsledkoch
    assert names(r) == ["Pilos Tvaroh měkký 250 g", "Madeta Tvaroh polotučný 250 g"]
    first = r.json()["items"][0]
    assert first["unit_price"] == "99.60" and first["unit_price_basis"] == "kg"
    assert first["conditions"] == [{"kind": "loyalty_card", "value": {"program": "Lidl Plus"}}]
    assert first["source"]["page"] == 1 and first["source"]["bbox"] == [0.5, 0.1, 0.4, 0.25]
    assert first["is_active"] is True


def test_search_ignores_diacritics_and_inflection(client):
    assert names(client.get("/v1/offers/search", params={"q": "mleko", "active_at": DAY})) == [
        "Mléko polotučné 1,5% 1 l"
    ]
    assert "Madeta Tvaroh polotučný 250 g" in names(
        client.get("/v1/offers/search", params={"q": "tvarohu", "active_at": DAY})
    )
    assert "Kuřecí prsní řízky" in names(client.get("/v1/offers/search", params={"q": "kureci", "active_at": DAY}))


def test_no_loyalty_and_price_filters(client):
    r = client.get("/v1/offers/search", params={"q": "tvaroh", "active_at": DAY, "no_loyalty": True})
    assert names(r) == ["Madeta Tvaroh polotučný 250 g"]
    r = client.get("/v1/offers/search", params={"active_at": DAY, "price_max": 20})
    assert names(r) == ["Mléko polotučné 1,5% 1 l"]


def test_validity_filters(client):
    # pivo platí až od 26. 9.
    today = names(client.get("/v1/offers/search", params={"q": "pivo", "active_at": DAY, "validity": "today"}))
    future = names(client.get("/v1/offers/search", params={"q": "pivo", "active_at": DAY, "validity": "future"}))
    assert today == [] and future == ["Pivo Plzeň 12° 0,5 l"]
    after = names(client.get("/v1/offers/search", params={"active_at": "2026-10-01"}))
    assert after == []


def test_active_offers_rank_before_future(client):
    items = client.get("/v1/offers/search", params={"active_at": DAY, "sort": "relevance"}).json()["items"]
    flags = [o["is_active"] for o in items]
    assert flags == sorted(flags, reverse=True)


def test_search_is_audited(client, session):
    client.get("/v1/offers/search", params={"q": "tvaroh", "active_at": DAY})
    event = session.scalar(select(ApiAuditEvent))
    assert event.action == "search_offers" and event.result_count == 2 and event.params["q"] == "tvaroh"


def test_offer_detail_and_404(client, session):
    offer_id = session.scalar(select(Offer.id).where(Offer.raw_name.like("Madeta%")))
    r = client.get(f"/v1/offers/{offer_id}", params={"active_at": DAY})
    assert r.status_code == 200
    body = r.json()
    assert body["price"] == "29.90" and body["regular_price"] == "39.90"
    assert body["valid_from"] == "2026-09-23" and body["valid_to"] == "2026-09-29"
    assert body["source"]["document_url"] is None  # lokálna cesta sa neposiela von
    assert client.get("/v1/offers/999999").status_code == 404


def test_stores_flyers_categories(client):
    assert [s["code"] for s in client.get("/v1/stores").json()] == ["testmarket"]
    flyers = client.get("/v1/flyers", params={"active_at": DAY}).json()
    assert len(flyers) == 1 and flyers[0]["page_count"] == 2 and flyers[0]["valid_to"] == "2026-09-29"
    assert client.get("/v1/categories").json() == []


def test_admin_requires_token(client):
    assert client.get("/v1/admin/runs").status_code == 401
    runs = client.get("/v1/admin/runs", headers=ADMIN).json()
    assert runs[0]["status"] == "succeeded" and runs[0]["offers_count"] == 6


def test_review_approve_makes_offer_searchable(client):
    queue = client.get("/v1/admin/review", headers=ADMIN).json()
    item = next(e for e in queue if e["code"] == "validity_outside_flyer")
    r = client.post(f"/v1/admin/review/{item['id']}", json={"action": "approve"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert "Tvaroh tučný 250 g" in names(client.get("/v1/offers/search", params={"q": "tvaroh", "active_at": DAY}))
    again = client.post(f"/v1/admin/review/{item['id']}", json={"action": "approve"}, headers=ADMIN)
    assert again.status_code == 409


def test_review_fix_creates_new_row_and_supersedes_old(client, session):
    queue = client.get("/v1/admin/review", headers=ADMIN).json()
    item = next(e for e in queue if e["code"] == "regular_below_price")
    r = client.post(
        f"/v1/admin/review/{item['id']}",
        json={"action": "fix", "correction": {"regular_price": "69.90"}},
        headers=ADMIN,
    )
    assert r.status_code == 200 and r.json()["status"] == "fixed"
    rows = session.scalars(select(Offer).where(Offer.raw_name == "Máslo 250 g").order_by(Offer.id)).all()
    old, new = rows
    assert old.superseded_by == new.id and old.price == new.price
    assert str(new.regular_price) == "69.90" and new.status == "active"
    assert names(client.get("/v1/offers/search", params={"q": "maslo", "active_at": DAY})) == ["Máslo 250 g"]
    assert session.scalar(select(func.count(Offer.id)).where(Offer.raw_name == "Máslo 250 g")) == 2
