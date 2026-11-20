"""Shared fixtures: temporary SQLite DB and TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "test.db"
    application = create_app(db_path=db_file)
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-User-Id": "2"}


@pytest.fixture()
def user_headers() -> dict[str, str]:
    return {"X-User-Id": "1"}


@pytest.fixture()
def other_user_headers() -> dict[str, str]:
    """Другий звичайний User (carol), не власник Bill Alice."""
    return {"X-User-Id": "3"}


def create_product(client: TestClient, admin_headers: dict[str, str], **overrides):
    payload = {
        "name": "Cyber Quest",
        "description": "Action RPG",
        "price": 29.99,
        "stock": 10,
        "category": "rpg",
    }
    payload.update(overrides)
    response = client.post("/api/products", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()
