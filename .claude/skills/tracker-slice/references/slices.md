# Зрізи навчального Luden API (ЛР 2)

## A. Каталог: створення й читання Product

- Код (`app/`): `schemas.py`, `services.py`, `routes.py`, `database.py`
- Тести (`tests/`): `conftest.py`, `test_products.py`
- Читати: `docs/lr2-api.md` — POST/GET `/api/products`, GET `/api/products/{id}`; `docs/requirements.md` — SRC-02, BR-04 (читання), §4.3 Product
- Критерії: AC-03.1, AC-05.1–05.2 (API-еквівалент); створення лише Admin
- Сценарії: T01, T02, T03, T13; негативи 401/403 на create

## B. Зміни Product і стани Bill

- Код (`app/`): `schemas.py`, `services.py`, `routes.py` — **не** змінювати `database.py` у цьому зрізі (схема Bill уже в каркасі)
- Тести (`tests/`): `test_products.py`, `test_bills.py` — не створювати нові файли схем БД
- Читати: `docs/lr2-api.md` — PATCH Product, POST/GET Bill, PATCH `/api/bills/{id}/status` (власник **або** Admin); `docs/requirements.md` — §5 матриця 25 клітинок, BR-06, BR-07, BR-11
- Критерії: AC-07.* (без Stripe), AC-09.1 (presence-aware PATCH); Т→200 без UPDATE; Н→409 без зміни запису
- Сценарії: T07, T08, T09, T10, T14; `test_bill_status_matrix_25_cells`; Admin read/PATCH чужого Bill
- Примітка v1: після AI-draft агент пропонував зайвий індекс/`bill_events` — заборонено; лише матриця переходів і тести статусів

## C. Позиції Bill і бібліотека

- Код (`app/`): `schemas.py`, `services.py`, `routes.py`
- Тести (`tests/`): `test_bills.py`, `test_library.py`
- Читати: `docs/lr2-api.md` — items у Bill, повторна покупка 409, GET `/api/users/{id}/library` (лише власник); `docs/requirements.md` — SRC-03, SRC-05, BR-05, BR-08
- Критерії: AC-06.1, AC-07.3, AC-08.2–08.3; Pending/Processing/Declined **не** в бібліотеці; Paid/Completed блокують repurchase
- Сценарії: T11, T12; атомарність create; multi-item total; library forbidden (у т.ч. Admin)

## D. Фільтри каталогу

- Код (`app/`): `schemas.py`, `services.py` (`normalize_filter`, `matches_query`, `matches_category`), `routes.py`
- Тести (`tests/`): `test_products.py` — T04–T06, `test_matches_*_predicate`, `test_normalize_filter_and_equals_ci_pair`
- Читати: `docs/lr2-api.md` — query `q`, `category`; `docs/requirements.md` — SRC-02, BR-04, AC-04.*
- Критерії: AC-04.1–04.4 (AND тексту й жанру); порожній параметр = без фільтра
- Сценарії: T04, T05, T06
- Експеримент AI/no-AI: **не** порівнювати `matches_query` з `matches_category` (різний принцип); див. `experiments/protocol.md` (`equals_ci` / `role_equals_ci`)

## E. Профіль власника (`GET /api/users/{id}`)

- Код (`app/`): `routes.py` (`get_user`), за потреби `services.py` (`require_user`, `row_to_user`) — **не** змінювати `database.py`
- Тести (`tests/`): `test_users.py` (і лише пов’язані правки в інших тестах, якщо вони викликають цей маршрут)
- Читати: `docs/lr2-api.md` — маршрут 9 `GET /api/users/{id}` (лише власник, `X-User-Id`); `docs/requirements.md` — SRC-06, BR-03 (профіль лише власнику)
- Критерії: власний профіль → 200; чужий (у т.ч. Admin не свій) → 403; неіснуючий id → 404; без заголовка → 401
- Сценарії: профіль Alice/Carol/Bob; Admin→Alice 403; missing user 404
