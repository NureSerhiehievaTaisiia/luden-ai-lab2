"""Library access for slice C (BR-03 / BR-08)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import create_product


def _flow_to(client: TestClient, headers: dict[str, str], bill_id: int, status: str):
    response = client.patch(
        f"/api/bills/{bill_id}/status",
        json={"status": status},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_library_empty_and_forbidden(
    client: TestClient,
    user_headers: dict[str, str],
    other_user_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    empty = client.get("/api/users/1/library", headers=user_headers)
    assert empty.status_code == 200
    assert empty.json() == []

    forbidden_admin = client.get("/api/users/2/library", headers=user_headers)
    assert forbidden_admin.status_code == 403

    foreign_user = client.get("/api/users/1/library", headers=other_user_headers)
    assert foreign_user.status_code == 403

    admin_foreign = client.get("/api/users/1/library", headers=admin_headers)
    assert admin_foreign.status_code == 403

    admin_own = client.get("/api/users/2/library", headers=admin_headers)
    assert admin_own.status_code == 200
    assert admin_own.json() == []

    no_header = client.get("/api/users/1/library")
    assert no_header.status_code == 401


def test_library_excludes_non_paid_statuses(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    pending_game = create_product(client, admin_headers, name="Pending Only")
    declined_game = create_product(client, admin_headers, name="Declined Only")

    pending_bill = client.post(
        "/api/bills",
        json={"productIds": [pending_game["id"]]},
        headers=user_headers,
    ).json()
    _flow_to(client, user_headers, pending_bill["id"], "Processing")

    declined_bill = client.post(
        "/api/bills",
        json={"productIds": [declined_game["id"]]},
        headers=user_headers,
    ).json()
    _flow_to(client, user_headers, declined_bill["id"], "Processing")
    _flow_to(client, user_headers, declined_bill["id"], "Declined")

    library = client.get("/api/users/1/library", headers=user_headers)
    assert library.status_code == 200
    assert library.json() == []


def test_library_after_completed(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
):
    product = create_product(client, admin_headers, name="Completed Title")
    bill = client.post(
        "/api/bills",
        json={"productIds": [product["id"]]},
        headers=user_headers,
    ).json()
    for status in ("Processing", "Paid", "Completed"):
        response = client.patch(
            f"/api/bills/{bill['id']}/status",
            json={"status": status},
            headers=user_headers,
        )
        assert response.status_code == 200

    library = client.get("/api/users/1/library", headers=user_headers)
    assert [p["name"] for p in library.json()] == ["Completed Title"]


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
