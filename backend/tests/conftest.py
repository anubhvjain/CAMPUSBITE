import os

os.environ["DATABASE_URL"] = "sqlite:///./test_campusbite.db"
os.environ["ENABLE_BACKGROUND_TASKS"] = "false"
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client, email, role="customer", **extra):
    body = {"name": email.split("@")[0], "email": email, "password": "secret123", "role": role, **extra}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture
def world(client):
    cust_h, cust = register(client, "cust@test.com", address="Hostel 1")
    cust2_h, _ = register(client, "cust2@test.com")
    owner_h, _ = register(client, "owner@test.com", role="restaurant_owner", restaurant_name="Testaurant")
    owner2_h, _ = register(client, "owner2@test.com", role="restaurant_owner")
    partner_h, partner = register(client, "partner@test.com", role="delivery_partner")
    partner2_h, _ = register(client, "partner2@test.com", role="delivery_partner")
    item = client.post("/api/owner/menu", json={"name": "Pizza", "price": "100.00"}, headers=owner_h).json()
    item2 = client.post("/api/owner/menu", json={"name": "Coke", "price": "40.00"}, headers=owner_h).json()
    rid = item["restaurant_id"]
    return dict(cust_h=cust_h, cust=cust, cust2_h=cust2_h, owner_h=owner_h, owner2_h=owner2_h,
                partner_h=partner_h, partner=partner, partner2_h=partner2_h, item=item, item2=item2, rid=rid)


def place(client, w, qty=2):
    r = client.post(
        "/api/orders",
        json={"restaurant_id": w["rid"], "items": [{"menu_item_id": w["item"]["id"], "quantity": qty},
                                                     {"menu_item_id": w["item2"]["id"], "quantity": 1}],
              "delivery_address": "Hostel 1"},
        headers=w["cust_h"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def deliver(client, w, oid):
    for s in ("ACCEPTED", "PREPARING", "READY"):
        assert client.patch(f"/api/owner/orders/{oid}/status", json={"status": s}, headers=w["owner_h"]).status_code == 200
    r = client.post(f"/api/owner/orders/{oid}/assign", json={"delivery_partner_id": w["partner"]["id"]}, headers=w["owner_h"])
    assert r.status_code == 200, r.text
    for s in ("OUT_FOR_DELIVERY", "DELIVERED"):
        r = client.patch(f"/api/delivery/orders/{oid}/status", json={"status": s}, headers=w["partner_h"])
        assert r.status_code == 200, r.text
    return r.json()
