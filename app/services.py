"""Business rules for educational Luden API."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.schemas import BillStatus, ProductCreate, ProductPatch

# From docs/requirements.md §5 (Д / Т / Н)
ALLOWED_TRANSITIONS: dict[BillStatus, set[BillStatus]] = {
    BillStatus.PENDING: {BillStatus.PENDING, BillStatus.PROCESSING},
    BillStatus.PROCESSING: {
        BillStatus.PROCESSING,
        BillStatus.DECLINED,
        BillStatus.PAID,
    },
    BillStatus.DECLINED: {BillStatus.DECLINED, BillStatus.PROCESSING},
    BillStatus.PAID: {BillStatus.PAID, BillStatus.COMPLETED},
    BillStatus.COMPLETED: {BillStatus.COMPLETED},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price": row["price"],
        "stock": row["stock"],
        "category": row["category"],
        "sales_count": row["sales_count"],
        "created_at": row["created_at"],
    }


def row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
    }


def normalize_filter(value: str | None) -> str | None:
    """Shared optional-filter token: None/blank → no filter; else stripped lowercased token."""
    if value is None:
        return None
    token = value.strip().lower()
    return token if token else None


def equals_ci(left: str, right: str) -> bool:
    """Case-insensitive exact equality (same check principle as role_equals_ci)."""
    return left.lower() == right.lower()


def role_equals_ci(left: str, right: str) -> bool:
    """Case-insensitive exact equality for role/status labels (paired with equals_ci)."""
    return left.lower() == right.lower()


def matches_query(product: dict[str, Any], value: str | None) -> bool:
    """Return True if product name matches substring filter; None means no filter."""
    needle = normalize_filter(value)
    if needle is None:
        return True
    return needle in str(product.get("name", "")).lower()


def matches_category(product: dict[str, Any], value: str | None) -> bool:
    """Return True if product category matches exact filter; None means no filter."""
    expected = normalize_filter(value)
    if expected is None:
        return True
    return equals_ci(str(product.get("category", "")), expected)


def require_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return row


def require_admin(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    user = require_user(conn, user_id)
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def create_product(conn: sqlite3.Connection, data: ProductCreate) -> dict[str, Any]:
    created = utc_now()
    cur = conn.execute(
        """
        INSERT INTO products (name, description, price, stock, category, sales_count, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (data.name, data.description, data.price, data.stock, data.category, created),
    )
    product_id = cur.lastrowid
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    assert row is not None
    return row_to_product(row)


def get_product(conn: sqlite3.Connection, product_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return row_to_product(row)


def list_products(
    conn: sqlite3.Connection,
    q: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    products = [row_to_product(r) for r in rows]
    return [
        p
        for p in products
        if matches_query(p, q) and matches_category(p, category)
    ]


def patch_product(
    conn: sqlite3.Connection,
    product_id: int,
    data: ProductPatch,
) -> dict[str, Any]:
    get_product(conn, product_id)
    updates: dict[str, Any] = {}
    mapping = {
        "name": "name",
        "description": "description",
        "price": "price",
        "stock": "stock",
        "category": "category",
    }
    for field, column in mapping.items():
        if field in data.model_fields_set:
            value = getattr(data, field)
            updates[column] = value

    if not updates:
        raise HTTPException(status_code=422, detail="No updatable fields")

    assignments = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [product_id]
    conn.execute(f"UPDATE products SET {assignments} WHERE id = ?", params)
    return get_product(conn, product_id)


def _bill_items(conn: sqlite3.Connection, bill_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id ASC
        """,
        (bill_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "product_id": r["product_id"],
            "quantity": r["quantity"],
            "price_at_purchase": r["price_at_purchase"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def bill_to_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "currency": row["currency"],
        "total_amount": row["total_amount"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "items": _bill_items(conn, row["id"]),
    }


def create_bill(
    conn: sqlite3.Connection,
    user_id: int,
    product_ids: list[int],
) -> dict[str, Any]:
    require_user(conn, user_id)
    created = utc_now()
    products: list[sqlite3.Row] = []
    for pid in product_ids:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found")
        owned = conn.execute(
            """
            SELECT 1
            FROM bill_items bi
            JOIN bills b ON b.id = bi.bill_id
            WHERE b.user_id = ?
              AND bi.product_id = ?
              AND b.status IN ('Paid', 'Completed')
            LIMIT 1
            """,
            (user_id, pid),
        ).fetchone()
        if owned is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Product {pid} already purchased",
            )
        products.append(row)

    total = sum(float(p["price"]) for p in products)
    cur = conn.execute(
        """
        INSERT INTO bills (user_id, currency, total_amount, status, created_at, updated_at)
        VALUES (?, 'UAH', ?, 'Pending', ?, NULL)
        """,
        (user_id, total, created),
    )
    bill_id = cur.lastrowid
    for product in products:
        conn.execute(
            """
            INSERT INTO bill_items (
                bill_id, product_id, quantity, price_at_purchase, created_at
            ) VALUES (?, ?, 1, ?, ?)
            """,
            (bill_id, product["id"], product["price"], created),
        )
    row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    assert row is not None
    return bill_to_dict(conn, row)


def get_bill(conn: sqlite3.Connection, bill_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill_to_dict(conn, row)


def transition_bill(
    conn: sqlite3.Connection,
    bill_id: int,
    actor_id: int,
    new_status: BillStatus,
) -> dict[str, Any]:
    require_user(conn, actor_id)
    row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    if int(row["user_id"]) != actor_id:
        actor = require_user(conn, actor_id)
        if actor["role"] != "Admin":
            raise HTTPException(status_code=403, detail="Not bill owner")

    current = BillStatus(row["status"])
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Transition {current.value} -> {new_status.value} is forbidden",
        )

    if new_status == current:
        return bill_to_dict(conn, row)

    updated = utc_now()
    conn.execute(
        "UPDATE bills SET status = ?, updated_at = ? WHERE id = ?",
        (new_status.value, updated, bill_id),
    )

    if current == BillStatus.PROCESSING and new_status == BillStatus.PAID:
        items = conn.execute(
            "SELECT product_id, quantity FROM bill_items WHERE bill_id = ?",
            (bill_id,),
        ).fetchall()
        for item in items:
            conn.execute(
                "UPDATE products SET sales_count = sales_count + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

    row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    assert row is not None
    return bill_to_dict(conn, row)


def get_library(conn: sqlite3.Connection, owner_id: int, actor_id: int) -> list[dict[str, Any]]:
    require_user(conn, actor_id)
    if owner_id != actor_id:
        raise HTTPException(status_code=403, detail="Cannot read another library")

    rows = conn.execute(
        """
        SELECT DISTINCT p.*
        FROM products p
        JOIN bill_items bi ON bi.product_id = p.id
        JOIN bills b ON b.id = bi.bill_id
        WHERE b.user_id = ? AND b.status IN ('Paid', 'Completed')
        ORDER BY p.id ASC
        """,
        (owner_id,),
    ).fetchall()
    return [row_to_product(r) for r in rows]
