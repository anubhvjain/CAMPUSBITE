from datetime import timedelta
from unittest.mock import patch

from app.database import SessionLocal
from app.models import Order, ReminderLog, utcnow
from app.tasks import generate_reminders
from tests.conftest import deliver, place, register


def test_register_login_me(client):
    register(client, "alice@test.com")
    assert client.post("/api/auth/register", json={"name": "aa", "email": "alice@test.com", "password": "secret123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "alice@test.com", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "alice@test.com", "password": "secret123"})
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "customer"
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_rbac(client, world):
    w = world
    assert client.get("/api/owner/orders", headers=w["cust_h"]).status_code == 403
    assert client.get("/api/delivery/orders", headers=w["owner_h"]).status_code == 403
    assert client.post("/api/orders", json={}, headers=w["owner_h"]).status_code == 403
    assert client.post("/api/ai/insights", json={}, headers=w["partner_h"]).status_code == 403


def test_place_order_mock_payment(client, world):
    o = place(client, world)
    assert o["status"] == "PLACED"
    assert o["payment_status"] == "mock_paid"
    assert float(o["total_amount"]) == 240.0
    assert len(o["payments"]) == 1 and o["payments"][0]["entry_type"] == "payment"


def test_unavailable_item_rejected(client, world):
    w = world
    client.patch(f"/api/owner/menu/{w['item']['id']}/availability", json={"is_available": False}, headers=w["owner_h"])
    r = client.post("/api/orders", json={"restaurant_id": w["rid"], "items": [{"menu_item_id": w["item"]["id"], "quantity": 1}],
                                         "delivery_address": "x y z"}, headers=w["cust_h"])
    assert r.status_code == 400


def test_order_isolation(client, world):
    w = world
    o = place(client, w)
    assert client.get(f"/api/orders/{o['id']}", headers=w["cust2_h"]).status_code == 404
    assert client.post(f"/api/orders/{o['id']}/cancel", headers=w["cust2_h"]).status_code == 404
    assert client.patch(f"/api/owner/orders/{o['id']}/status", json={"status": "ACCEPTED"}, headers=w["owner2_h"]).status_code == 404
    assert client.get("/api/orders/my", headers=w["cust2_h"]).json()["total"] == 0


def test_full_lifecycle_and_partner_scope(client, world):
    w = world
    o = place(client, w)
    oid = o["id"]
    # assigning before READY is rejected
    r = client.post(f"/api/owner/orders/{oid}/assign", json={"delivery_partner_id": w["partner"]["id"]}, headers=w["owner_h"])
    assert r.status_code == 400
    for s in ("ACCEPTED", "PREPARING", "READY"):
        client.patch(f"/api/owner/orders/{oid}/status", json={"status": s}, headers=w["owner_h"])
    client.post(f"/api/owner/orders/{oid}/assign", json={"delivery_partner_id": w["partner"]["id"]}, headers=w["owner_h"])
    # other partner can't see / update
    assert client.get("/api/delivery/orders", headers=w["partner2_h"]).json()["total"] == 0
    assert client.patch(f"/api/delivery/orders/{oid}/status", json={"status": "OUT_FOR_DELIVERY"}, headers=w["partner2_h"]).status_code == 404
    # skipping a step is rejected
    assert client.patch(f"/api/delivery/orders/{oid}/status", json={"status": "DELIVERED"}, headers=w["partner_h"]).status_code == 400
    lst = client.get("/api/delivery/orders", headers=w["partner_h"]).json()
    assert lst["items"][0]["customer"]["address"] == "Hostel 1"
    client.patch(f"/api/delivery/orders/{oid}/status", json={"status": "OUT_FOR_DELIVERY"}, headers=w["partner_h"])
    r = client.patch(f"/api/delivery/orders/{oid}/status", json={"status": "DELIVERED"}, headers=w["partner_h"])
    assert r.json()["status"] == "DELIVERED"
    assert client.get("/api/delivery/history", headers=w["partner_h"]).json()["total"] == 1
    # delivered orders can't be cancelled
    assert client.post(f"/api/orders/{oid}/cancel", headers=w["cust_h"]).status_code == 400


def test_invalid_owner_transitions(client, world):
    w = world
    oid = place(client, w)["id"]
    assert client.patch(f"/api/owner/orders/{oid}/status", json={"status": "READY"}, headers=w["owner_h"]).status_code == 400
    assert client.patch(f"/api/owner/orders/{oid}/status", json={"status": "DELIVERED"}, headers=w["owner_h"]).status_code == 400


def test_cancel_only_when_placed(client, world):
    w = world
    o1 = place(client, w)
    r = client.post(f"/api/orders/{o1['id']}/cancel", headers=w["cust_h"])
    assert r.json()["status"] == "CANCELLED"
    o2 = place(client, w)
    client.patch(f"/api/owner/orders/{o2['id']}/status", json={"status": "ACCEPTED"}, headers=w["owner_h"])
    assert client.post(f"/api/orders/{o2['id']}/cancel", headers=w["cust_h"]).status_code == 400


def test_review_and_return_flow(client, world):
    w = world
    oid = place(client, w)["id"]
    assert client.post(f"/api/orders/{oid}/review", json={"rating": 5}, headers=w["cust_h"]).status_code == 400
    assert client.post(f"/api/orders/{oid}/return", json={"reason": "Cold food"}, headers=w["cust_h"]).status_code == 400
    deliver(client, w, oid)
    assert client.post(f"/api/orders/{oid}/review", json={"rating": 4, "comment": "ok"}, headers=w["cust_h"]).status_code == 201
    assert client.post(f"/api/orders/{oid}/review", json={"rating": 4}, headers=w["cust_h"]).status_code == 409
    r = client.post(f"/api/orders/{oid}/return", json={"reason": "Cold food"}, headers=w["cust_h"])
    assert r.status_code == 201
    assert client.post(f"/api/orders/{oid}/return", json={"reason": "Again please"}, headers=w["cust_h"]).status_code == 409
    rid = r.json()["id"]
    assert client.post(f"/api/owner/returns/{rid}/approve", headers=w["owner2_h"]).status_code == 404
    r = client.post(f"/api/owner/returns/{rid}/approve", json={"note": "Sorry"}, headers=w["owner_h"])
    assert r.json()["status"] == "approved"
    d = client.get(f"/api/orders/{oid}", headers=w["cust_h"]).json()
    assert d["payment_status"] == "refunded" and d["status"] == "REFUNDED" and d["return_status"] == "approved"
    assert [p["entry_type"] for p in d["payments"]] == ["payment", "refund"]
    assert client.post(f"/api/owner/returns/{rid}/reject", headers=w["owner_h"]).status_code == 409


def test_return_reject(client, world):
    w = world
    oid = place(client, w)["id"]
    deliver(client, w, oid)
    rid = client.post(f"/api/orders/{oid}/return", json={"reason": "Wrong item"}, headers=w["cust_h"]).json()["id"]
    client.post(f"/api/owner/returns/{rid}/reject", headers=w["owner_h"])
    d = client.get(f"/api/orders/{oid}", headers=w["cust_h"]).json()
    assert d["return_status"] == "rejected" and d["payment_status"] == "mock_paid"


def test_filters_pagination_stats(client, world):
    w = world
    for _ in range(3):
        place(client, w)
    page = client.get("/api/orders/my?page=1&page_size=2", headers=w["cust_h"]).json()
    assert page["total"] == 3 and page["pages"] == 2 and len(page["items"]) == 2
    assert client.get("/api/owner/orders?status=ACCEPTED", headers=w["owner_h"]).json()["total"] == 0
    assert client.get("/api/owner/orders?status=PLACED", headers=w["owner_h"]).json()["total"] == 3
    stats = client.get("/api/owner/stats", headers=w["owner_h"]).json()
    assert stats["total_orders"] == 3 and float(stats["total_revenue"]) == 720.0
    menu = client.get(f"/api/restaurants/{w['rid']}/menu?search=piz&max_price=150", headers={}).json()
    assert [m["name"] for m in menu["items"]] == ["Pizza"]


def test_reminders(client, world):
    w = world
    oid = place(client, w)["id"]
    db = SessionLocal()
    try:
        db.get(Order, oid).updated_at = utcnow() - timedelta(minutes=20)
        db.commit()
        assert generate_reminders(db) == 1
        assert generate_reminders(db) == 0
        assert db.query(ReminderLog).count() == 1
    finally:
        db.close()
    rems = client.get("/api/owner/reminders", headers=w["owner_h"]).json()
    assert rems["total"] == 1
    assert client.get("/api/owner/reminders", headers=w["owner2_h"]).json()["total"] == 0
    client.patch(f"/api/owner/orders/{oid}/status", json={"status": "ACCEPTED"}, headers=w["owner_h"])
    assert client.get("/api/owner/reminders", headers=w["owner_h"]).json()["total"] == 0


def test_ai_missing_key_and_isolation(client, world):
    w = world
    place(client, w)
    assert client.post("/api/ai/insights", json={}, headers=w["cust_h"]).status_code == 503
    r = client.post("/api/ai/insights", json={}, headers=w["cust2_h"])
    assert r.status_code == 200 and r.json()["orders_considered"] == 0

    captured = {}

    def fake(orders, question, today):
        captured["ids"] = {o.customer_id for o in orders}
        return "summary"

    with patch("app.routers.ai.ask_openai", side_effect=fake):
        r = client.post("/api/ai/insights", json={"question": "How much did I spend?"}, headers=w["cust_h"])
    assert r.json()["answer"] == "summary"
    assert captured["ids"] == {w["cust"]["id"]}
