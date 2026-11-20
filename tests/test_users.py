"""Профіль: доступ лише власнику (BR-03)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_own_profile(
    client: TestClient,
    user_headers: dict[str, str],
):
    response = client.get("/api/users/1", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["username"] == "alice"
    assert body["role"] == "User"


def test_get_foreign_profile_forbidden(
    client: TestClient,
    user_headers: dict[str, str],
):
    response = client.get("/api/users/3", headers=user_headers)
    assert response.status_code == 403


def test_admin_cannot_read_foreign_profile(
    client: TestClient,
    admin_headers: dict[str, str],
):
    foreign = client.get("/api/users/1", headers=admin_headers)
    assert foreign.status_code == 403

    own = client.get("/api/users/2", headers=admin_headers)
    assert own.status_code == 200
    assert own.json()["username"] == "bob"


def test_get_missing_profile(
    client: TestClient,
    user_headers: dict[str, str],
):
    response = client.get("/api/users/999", headers=user_headers)
    assert response.status_code == 404


def test_get_profile_requires_header(client: TestClient):
    response = client.get("/api/users/1")
    assert response.status_code == 401
