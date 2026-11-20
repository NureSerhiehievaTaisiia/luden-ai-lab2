"""HTTP routes for educational Luden API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app import services
from app.database import get_connection
from app.schemas import (
    BillCreate,
    BillOut,
    ProductCreate,
    ProductOut,
    ProductPatch,
    StatusPatch,
    UserOut,
)

router = APIRouter()


def db_path_dep(request: Request) -> str:
    return request.app.state.db_path


def parse_user_id(x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None) -> int:
    if x_user_id is None or not str(x_user_id).strip():
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="X-User-Id must be an integer") from exc


DbPath = Annotated[str, Depends(db_path_dep)]
UserId = Annotated[int, Depends(parse_user_id)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db_path: DbPath, actor_id: UserId) -> UserOut:
    with get_connection(db_path) as conn:
        services.require_user(conn, actor_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        if actor_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot read another profile")
        return UserOut.model_validate(services.row_to_user(row))


@router.post("/api/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, db_path: DbPath, user_id: UserId) -> ProductOut:
    with get_connection(db_path) as conn:
        services.require_admin(conn, user_id)
        return ProductOut.model_validate(services.create_product(conn, body))


@router.get("/api/products", response_model=list[ProductOut])
def list_products(
    db_path: DbPath,
    q: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
) -> list[ProductOut]:
    with get_connection(db_path) as conn:
        items = services.list_products(conn, q=q, category=category)
        return [ProductOut.model_validate(p) for p in items]


@router.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db_path: DbPath) -> ProductOut:
    with get_connection(db_path) as conn:
        return ProductOut.model_validate(services.get_product(conn, product_id))


@router.patch("/api/products/{product_id}", response_model=ProductOut)
def patch_product(
    product_id: int,
    body: ProductPatch,
    db_path: DbPath,
    user_id: UserId,
) -> ProductOut:
    with get_connection(db_path) as conn:
        services.require_admin(conn, user_id)
        return ProductOut.model_validate(services.patch_product(conn, product_id, body))


@router.post("/api/bills", response_model=BillOut, status_code=201)
def create_bill(body: BillCreate, db_path: DbPath, user_id: UserId) -> BillOut:
    with get_connection(db_path) as conn:
        return BillOut.model_validate(
            services.create_bill(conn, user_id, body.product_ids)
        )


@router.get("/api/bills/{bill_id}", response_model=BillOut)
def get_bill(bill_id: int, db_path: DbPath, user_id: UserId) -> BillOut:
    with get_connection(db_path) as conn:
        bill = services.get_bill(conn, bill_id)
        if bill["user_id"] != user_id:
            actor = services.require_user(conn, user_id)
            if actor["role"] != "Admin":
                raise HTTPException(status_code=403, detail="Not bill owner")
        return BillOut.model_validate(bill)


@router.patch("/api/bills/{bill_id}/status", response_model=BillOut)
def patch_bill_status(
    bill_id: int,
    body: StatusPatch,
    db_path: DbPath,
    user_id: UserId,
) -> BillOut:
    with get_connection(db_path) as conn:
        return BillOut.model_validate(
            services.transition_bill(conn, bill_id, user_id, body.status)
        )


@router.get("/api/users/{user_id}/library", response_model=list[ProductOut])
def get_library(user_id: int, db_path: DbPath, actor_id: UserId) -> list[ProductOut]:
    with get_connection(db_path) as conn:
        items = services.get_library(conn, user_id, actor_id)
        return [ProductOut.model_validate(p) for p in items]
