"""Product catalog scenarios T01–T07, T13–T14 and filters T04–T06."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import (
    equals_ci,
    matches_category,
    matches_query,
    normalize_filter,
    role_equals_ci,
)
from tests.conftest import create_product


def test_t01_create_minimal_body(client: TestClient, admin_headers: dict[str, str]):
    response = client.post(
        "/api/products",
        json={"name": "Peak Climb", "price": 19.99},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] >= 1
    assert body["name"] == "Peak Climb"
    assert body["description"] == ""
    assert body["category"] == ""
    assert body["salesCount"] == 0
    assert body["price"] == 19.99


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("ab", 422),
        ("abc", 201),
        ("x" * 200, 201),
        ("x" * 201, 422),
        ("  ab  ", 422),
        ("  abc  ", 201),
    ],
)
def test_t02_name_trim_boundaries(
    client: TestClient,
    admin_headers: dict[str, str],
    title: str,
    expected: int,
):
    response = client.post(
        "/api/products",
        json={"name": title, "price": 9.99},
        headers=admin_headers,
    )
    assert response.status_code == expected
    if expected == 201:
        assert response.json()["name"] == title.strip()


def test_t03_list_and_detail(client: TestClient, admin_headers: dict[str, str]):
    a = create_product(client, admin_headers, name="Alpha Game")
    b = create_product(client, admin_headers, name="Beta Game", category="action")
    listing = client.get("/api/products")
    assert listing.status_code == 200
    names = [item["name"] for item in listing.json()]
    assert names == ["Alpha Game", "Beta Game"]

    detail = client.get(f"/api/products/{a['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Alpha Game"
    assert detail.json()["id"] == a["id"]

    missing = client.get("/api/products/9999")
    assert missing.status_code == 404
    assert b["id"] != a["id"]


def test_t04_filter_category_empty(client: TestClient, admin_headers: dict[str, str]):
    create_product(client, admin_headers, name="RPG One", category="rpg")
    create_product(client, admin_headers, name="Action One", category="action")
    response = client.get("/api/products", params={"category": "strategy"})
    assert response.status_code == 200
    assert response.json() == []


def test_t05_filter_query_and_unknown_category(
    client: TestClient,
    admin_headers: dict[str, str],
):
    create_product(client, admin_headers, name="Silksong", category="metroidvania")
    create_product(client, admin_headers, name="Cyberpunk", category="rpg")
    by_q = client.get("/api/products", params={"q": "silk"})
    assert by_q.status_code == 200
    assert [p["name"] for p in by_q.json()] == ["Silksong"]

    # Unknown category value simply yields empty intersection, not 422 —
    # category is free-form string in LR1; empty list + 200.
    empty = client.get("/api/products", params={"category": "no-such-genre"})
    assert empty.status_code == 200
    assert empty.json() == []


def test_t06_and_filters(client: TestClient, admin_headers: dict[str, str]):
    create_product(client, admin_headers, name="Dragon RPG", category="rpg")
    create_product(client, admin_headers, name="Dragon Action", category="action")
    create_product(client, admin_headers, name="Space RPG", category="rpg")
    create_product(client, admin_headers, name="Farm Sim", category="sim")

    response = client.get("/api/products", params={"q": "dragon", "category": "rpg"})
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert names == ["Dragon RPG"]

    empty_and = client.get(
        "/api/products",
        params={"q": "dragon", "category": "sim"},
    )
    assert empty_and.status_code == 200
    assert empty_and.json() == []


def test_filters_case_whitespace_and_empty_params(
    client: TestClient,
    admin_headers: dict[str, str],
):
    create_product(client, admin_headers, name="Silksong", category="Metroidvania")
    create_product(client, admin_headers, name="Cyberpunk", category="rpg")

    all_products = client.get("/api/products")
    assert all_products.status_code == 200
    assert len(all_products.json()) == 2

    assert [p["name"] for p in client.get("/api/products", params={"q": "SILK"}).json()] == [
        "Silksong"
    ]
    assert [p["name"] for p in client.get("/api/products", params={"q": "  silk  "}).json()] == [
        "Silksong"
    ]
    # Порожній q= не фільтрує
    assert len(client.get("/api/products", params={"q": ""}).json()) == 2
    assert [p["name"] for p in client.get("/api/products", params={"category": "METROIDVANIA"}).json()] == [
        "Silksong"
    ]
    assert len(client.get("/api/products", params={"category": ""}).json()) == 2


def test_user_cannot_create_or_patch_product(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    denied = client.post(
        "/api/products",
        json={"name": "User Attempt", "price": 5.0},
        headers=user_headers,
    )
    assert denied.status_code == 403
    product = create_product(client, admin_headers, name="Protected")
    denied_patch = client.patch(
        f"/api/products/{product['id']}",
        json={"name": "Hacked"},
        headers=user_headers,
    )
    assert denied_patch.status_code == 403

    no_header = client.post(
        "/api/products",
        json={"name": "No Header", "price": 5.0},
    )
    assert no_header.status_code == 401

    missing_patch = client.patch(
        "/api/products/99999",
        json={"description": "gone"},
        headers=admin_headers,
    )
    assert missing_patch.status_code == 404


def test_matches_query_predicate():
    product = {"name": "Dragon RPG", "category": "rpg"}
    assert matches_query(product, None) is True
    assert matches_query(product, "  ") is True
    assert matches_query(product, "dragon") is True
    assert matches_query(product, "DRAGON") is True
    assert matches_query(product, "space") is False


def test_matches_category_predicate():
    product = {"name": "Dragon RPG", "category": "rpg"}
    assert matches_category(product, None) is True
    assert matches_category(product, "rpg") is True
    assert matches_category(product, "RPG") is True
    assert matches_category(product, "action") is False


def test_normalize_filter_and_equals_ci_pair():
    assert normalize_filter(None) is None
    assert normalize_filter("  ") is None
    assert normalize_filter(" RPG ") == "rpg"
    assert equals_ci("Rpg", "rpg") is True
    assert equals_ci("Rpg", "action") is False
    assert role_equals_ci("Admin", "admin") is True
    assert role_equals_ci("User", "Admin") is False
    assert equals_ci("A", "a") == role_equals_ci("A", "a")


def test_t07_partial_patch(
    client: TestClient,
    admin_headers: dict[str, str],
):
    product = create_product(
        client,
        admin_headers,
        name="Original Title",
        price=10.0,
        stock=5,
        category="rpg",
    )
    response = client.patch(
        f"/api/products/{product['id']}",
        json={"description": "Updated text"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated text"
    assert body["name"] == "Original Title"
    assert body["price"] == 10.0
    assert body["stock"] == 5
    assert body["category"] == "rpg"

    null_name = client.patch(
        f"/api/products/{product['id']}",
        json={"name": None},
        headers=admin_headers,
    )
    assert null_name.status_code == 422

    null_price = client.patch(
        f"/api/products/{product['id']}",
        json={"price": None},
        headers=admin_headers,
    )
    assert null_price.status_code == 422


def test_t13_persistence_across_restart(
    tmp_path,
    admin_headers: dict[str, str],
):
    db_file = tmp_path / "persist.db"
    app1 = create_app(db_path=db_file)
    with TestClient(app1) as c1:
        created = create_product(c1, admin_headers, name="Persistent Game")
        product_id = created["id"]

    app2 = create_app(db_path=db_file)
    with TestClient(app2) as c2:
        response = c2.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Persistent Game"
        users = c2.get("/api/users/1", headers={"X-User-Id": "1"})
        assert users.status_code == 200
        assert users.json()["username"] == "alice"
        assert (
            c2.get("/api/users/3", headers={"X-User-Id": "3"}).json()["username"]
            == "carol"
        )


def test_t14_empty_patch_unknown_and_immutable(
    client: TestClient,
    admin_headers: dict[str, str],
):
    product = create_product(client, admin_headers)
    empty = client.patch(
        f"/api/products/{product['id']}",
        json={},
        headers=admin_headers,
    )
    assert empty.status_code == 422

    unknown = client.patch(
        f"/api/products/{product['id']}",
        json={"unknownField": "x"},
        headers=admin_headers,
    )
    assert unknown.status_code == 422

    status_via_patch = client.patch(
        f"/api/products/{product['id']}",
        json={"salesCount": 99},
        headers=admin_headers,
    )
    assert status_via_patch.status_code == 422
