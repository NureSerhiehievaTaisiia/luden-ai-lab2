"""Сценарії Bill: T08–T12, матриця статусів, права, атомарність, знімок ціни."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.schemas import BillStatus
from app.services import ALLOWED_TRANSITIONS
from tests.conftest import create_product


def _flow_to(client: TestClient, headers: dict[str, str], bill_id: int, status: str):
    response = client.patch(
        f"/api/bills/{bill_id}/status",
        json={"status": status},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == status
    return response.json()


def _count_bills(client: TestClient) -> int:
    """Підрахунок Bill через тимчасову SQLite-базу тестового клієнта."""
    with sqlite3.connect(client.app.state.db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0])


def _count_items(client: TestClient) -> int:
    with sqlite3.connect(client.app.state.db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM bill_items").fetchone()[0])


def test_t08_owner_and_foreign_access(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    other_user_headers: dict[str, str],
):
    product = create_product(client, admin_headers)
    created = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    )
    assert created.status_code == 201
    bill = created.json()
    assert bill["userId"] == 1
    assert bill["status"] == "Pending"
    assert bill["currency"] == "UAH"
    assert len(bill["items"]) == 1
    assert bill["items"][0]["priceAtPurchase"] == product["price"]
    assert bill["totalAmount"] == product["price"]

    own = client.get(f"/api/bills/{bill['id']}", headers=user_headers)
    assert own.status_code == 200

    # Інший звичайний User (carol) не читає чужий Bill
    foreign = client.get(f"/api/bills/{bill['id']}", headers=other_user_headers)
    assert foreign.status_code == 403

    # Admin bob читає
    admin_read = client.get(f"/api/bills/{bill['id']}", headers=admin_headers)
    assert admin_read.status_code == 200

    # Чужий User не змінює статус
    foreign_status = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Processing"},
        headers=other_user_headers,
    )
    assert foreign_status.status_code == 403
    assert client.get(f"/api/bills/{bill['id']}", headers=user_headers).json()["status"] == "Pending"

    bad = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers={"X-User-Id": "99"},
    )
    assert bad.status_code == 401


def test_roles_user_admin_and_headers(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    denied_create = client.post(
        "/api/products",
        json={"name": "Denied Game", "price": 9.99},
        headers=user_headers,
    )
    assert denied_create.status_code == 403

    product = create_product(client, admin_headers, name="Admin Created")
    denied_patch = client.patch(
        f"/api/products/{product['id']}",
        json={"description": "hack"},
        headers=user_headers,
    )
    assert denied_patch.status_code == 403

    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    )
    assert bill.status_code == 201

    no_header = client.post("/api/bills", json={"productIds": [product["id"]]})
    assert no_header.status_code == 401

    bad_header = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers={"X-User-Id": "not-int"},
    )
    assert bad_header.status_code == 422


def test_t09_allowed_transition_and_repeat(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers)
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()

    first = _flow_to(client, user_headers, bill["id"], "Processing")
    assert first["status"] == "Processing"

    same = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Processing"},
        headers=user_headers,
    )
    assert same.status_code == 200
    assert same.json()["status"] == "Processing"
    assert same.json()["updatedAt"] == first.get("updatedAt")


def test_bill_status_matrix_and_sales_count(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Sales Tracked", price=15.0)
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()

    _flow_to(client, user_headers, bill["id"], "Processing")
    paid = _flow_to(client, user_headers, bill["id"], "Paid")
    assert paid["status"] == "Paid"
    after_paid = client.get(f"/api/products/{product['id']}").json()
    assert after_paid["salesCount"] == 1

    # Paid → Paid не збільшує sales_count повторно
    paid_again = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Paid"},
        headers=user_headers,
    )
    assert paid_again.status_code == 200
    assert client.get(f"/api/products/{product['id']}").json()["salesCount"] == 1

    completed = _flow_to(client, user_headers, bill["id"], "Completed")
    assert completed["status"] == "Completed"
    completed_again = _flow_to(client, user_headers, bill["id"], "Completed")
    assert completed_again["status"] == "Completed"
    assert completed_again["updatedAt"] == completed.get("updatedAt")

    for forbidden in ("Pending", "Processing"):
        response = client.patch(
            f"/api/bills/{bill['id']}/status",
            json={"status": forbidden},
            headers=user_headers,
        )
        assert response.status_code == 409
        check = client.get(f"/api/bills/{bill['id']}", headers=user_headers).json()
        assert check["status"] == "Completed"
        assert check["updatedAt"] == completed.get("updatedAt")

    unknown = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Refunded"},
        headers=user_headers,
    )
    assert unknown.status_code == 422

    missing = client.patch(
        "/api/bills/9999/status",
        json={"status": "Processing"},
        headers=user_headers,
    )
    assert missing.status_code == 404


def test_t10_forbidden_transition_preserves_status(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers)
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()
    _flow_to(client, user_headers, bill["id"], "Processing")
    paid = _flow_to(client, user_headers, bill["id"], "Paid")
    assert paid["status"] == "Paid"
    snapshot = client.get(f"/api/bills/{bill['id']}", headers=user_headers).json()

    forbidden = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Pending"},
        headers=user_headers,
    )
    assert forbidden.status_code == 409

    check = client.get(f"/api/bills/{bill['id']}", headers=user_headers)
    assert check.status_code == 200
    body = check.json()
    assert body["status"] == "Paid"
    assert body["updatedAt"] == snapshot["updatedAt"]
    assert body["totalAmount"] == snapshot["totalAmount"]
    assert body["items"] == snapshot["items"]


def test_bill_create_rejects_client_server_fields(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Field Guard")
    for payload in (
        {"productIds": [product["id"]], "userId": 3},
        {"productIds": [product["id"]], "status": "Paid"},
        {"productIds": [product["id"]], "totalAmount": 1.0},
        {"productIds": [product["id"]], "currency": "USD"},
        {"productIds": [product["id"]], "id": 999},
    ):
        response = client.post("/api/bills", json=payload, headers=user_headers)
        assert response.status_code == 422, payload


def test_t11_bill_items_validation(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Valid Game")
    ok = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    )
    assert ok.status_code == 201
    assert len(ok.json()["items"]) == 1

    empty = client.post("/api/bills", json={"productIds": []}, headers=user_headers)
    assert empty.status_code == 422

    dup = client.post(
        "/api/bills",
        json={"productIds": [product["id"], product["id"]]},
        headers=user_headers,
    )
    assert dup.status_code == 422


def test_bill_create_atomicity_no_partial_row(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Existing")
    before_bills = _count_bills(client)
    before_items = _count_items(client)

    response = client.post(
        "/api/bills",
        json={"productIds": [product["id"], 99999]},
        headers=user_headers,
    )
    assert response.status_code == 404
    assert _count_bills(client) == before_bills
    assert _count_items(client) == before_items


def test_price_at_purchase_snapshot(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Priced Game", price=100.0)
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()
    assert bill["items"][0]["priceAtPurchase"] == 100.0
    assert bill["totalAmount"] == 100.0

    patched = client.patch(
        f"/api/products/{product['id']}",
        json={"price": 200.0},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["price"] == 200.0

    reread = client.get(f"/api/bills/{bill['id']}", headers=user_headers).json()
    assert reread["items"][0]["priceAtPurchase"] == 100.0
    assert reread["totalAmount"] == 100.0


def test_t12_missing_product_and_library_after_paid(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    missing = client.post(
        "/api/bills",
        json={"productIds": [999]},
        headers=user_headers,
    )
    assert missing.status_code == 404

    product = create_product(client, admin_headers, name="Library Game")
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()

    before = client.get("/api/users/1/library", headers=user_headers)
    assert before.status_code == 200
    assert before.json() == []

    _flow_to(client, user_headers, bill["id"], "Processing")
    _flow_to(client, user_headers, bill["id"], "Paid")

    after = client.get("/api/users/1/library", headers=user_headers)
    assert after.status_code == 200
    assert [p["name"] for p in after.json()] == ["Library Game"]


def test_repurchase_blocked_after_paid_allows_after_declined(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    first_game = create_product(client, admin_headers, name="Owned Once")
    other_game = create_product(client, admin_headers, name="Other Title")
    declined_game = create_product(client, admin_headers, name="Declined Title")
    completed_game = create_product(client, admin_headers, name="Completed Once")

    first = client.post(
        "/api/bills",
        json={"productIds": [first_game["id"]]},
        headers=user_headers,
    )
    assert first.status_code == 201
    _flow_to(client, user_headers, first.json()["id"], "Processing")
    _flow_to(client, user_headers, first.json()["id"], "Paid")

    again = client.post(
        "/api/bills",
        json={"productIds": [first_game["id"]]},
        headers=user_headers,
    )
    assert again.status_code == 409
    assert _count_bills(client) == 1

    other = client.post(
        "/api/bills",
        json={"productIds": [other_game["id"]]},
        headers=user_headers,
    )
    assert other.status_code == 201

    declined = client.post(
        "/api/bills",
        json={"productIds": [declined_game["id"]]},
        headers=user_headers,
    )
    assert declined.status_code == 201
    _flow_to(client, user_headers, declined.json()["id"], "Processing")
    declined_status = client.patch(
        f"/api/bills/{declined.json()['id']}/status",
        json={"status": "Declined"},
        headers=user_headers,
    )
    assert declined_status.status_code == 200

    retry_declined = client.post(
        "/api/bills",
        json={"productIds": [declined_game["id"]]},
        headers=user_headers,
    )
    assert retry_declined.status_code == 201

    completed = client.post(
        "/api/bills",
        json={"productIds": [completed_game["id"]]},
        headers=user_headers,
    )
    assert completed.status_code == 201
    _flow_to(client, user_headers, completed.json()["id"], "Processing")
    _flow_to(client, user_headers, completed.json()["id"], "Paid")
    _flow_to(client, user_headers, completed.json()["id"], "Completed")
    again_completed = client.post(
        "/api/bills",
        json={"productIds": [completed_game["id"]]},
        headers=user_headers,
    )
    assert again_completed.status_code == 409


def test_multi_item_bill_total_and_invalid_ids(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    a = create_product(client, admin_headers, name="Bundle A", price=10.0)
    b = create_product(client, admin_headers, name="Bundle B", price=15.5)
    ok = client.post(
        "/api/bills",
        json={"productIds": [a["id"], b["id"]]},
        headers=user_headers,
    )
    assert ok.status_code == 201
    body = ok.json()
    assert body["totalAmount"] == 25.5
    assert len(body["items"]) == 2
    prices = sorted(item["priceAtPurchase"] for item in body["items"])
    assert prices == [10.0, 15.5]

    zero = client.post(
        "/api/bills",
        json={"productIds": [0]},
        headers=user_headers,
    )
    assert zero.status_code == 422
    negative = client.post(
        "/api/bills",
        json={"productIds": [-1]},
        headers=user_headers,
    )
    assert negative.status_code == 422


def test_admin_can_read_and_transition_foreign_bill(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Admin Flow")
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()
    no_header = client.get(f"/api/bills/{bill['id']}")
    assert no_header.status_code == 401

    admin_read = client.get(f"/api/bills/{bill['id']}", headers=admin_headers)
    assert admin_read.status_code == 200
    patched = client.patch(
        f"/api/bills/{bill['id']}/status",
        json={"status": "Processing"},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "Processing"


def _matrix_cases() -> list[tuple[str, str, int]]:
    cases: list[tuple[str, str, int]] = []
    for current in BillStatus:
        allowed = ALLOWED_TRANSITIONS[current]
        for target in BillStatus:
            expected = 200 if target in allowed else 409
            cases.append((current.value, target.value, expected))
    assert len(cases) == 25
    return cases


@pytest.mark.parametrize(("current", "target", "expected"), _matrix_cases())
def test_bill_status_matrix_25_cells(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    current: str,
    target: str,
    expected: int,
):
    """Усі 25 комбінацій матриці §5: Д/Т → 200, Н → 409 без зміни стану."""
    product = create_product(
        client,
        admin_headers,
        name=f"Matrix {current}->{target}",
        price=11.0,
    )
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()
    bill_id = bill["id"]

    path = {
        "Pending": [],
        "Processing": ["Processing"],
        "Declined": ["Processing", "Declined"],
        "Paid": ["Processing", "Paid"],
        "Completed": ["Processing", "Paid", "Completed"],
    }[current]
    for step in path:
        _flow_to(client, user_headers, bill_id, step)

    before = client.get(f"/api/bills/{bill_id}", headers=user_headers).json()
    assert before["status"] == current

    response = client.patch(
        f"/api/bills/{bill_id}/status",
        json={"status": target},
        headers=user_headers,
    )
    assert response.status_code == expected, response.text

    after = client.get(f"/api/bills/{bill_id}", headers=user_headers).json()
    if expected == 409:
        assert after["status"] == current
        assert after["updatedAt"] == before.get("updatedAt")
        assert after["items"] == before["items"]
        assert after["totalAmount"] == before["totalAmount"]
    else:
        assert after["status"] == target
        if target == current:
            assert after["updatedAt"] == before.get("updatedAt")
