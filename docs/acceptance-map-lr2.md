# Карта приймання ЛР2 — що перевіряти в коді (не лише в README)

Репозиторій: https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2  
Навчальний wire: [lr2-api.md](lr2-api.md). Адаптація MIT→Luden: [methodology-crosswalk.md](methodology-crosswalk.md).

Тема Luden (додаток Б) узгоджена з викладачем до тегу `lab02-skill-v0`. Письмового листа в репозиторії немає; підтвердження — усне / на занятті.

## 1. Дев’ять бізнес-маршрутів + health

| # | Метод і шлях | Файл | Функція |
| --- | --- | --- | --- |
| 0 | `GET /health` | `app/routes.py` | `health` |
| 1 | `POST /api/products` | `app/routes.py` | `create_product` |
| 2 | `GET /api/products` | `app/routes.py` | `list_products` |
| 3 | `GET /api/products/{id}` | `app/routes.py` | `get_product` |
| 4 | `PATCH /api/products/{id}` | `app/routes.py` | `patch_product` |
| 5 | `POST /api/bills` | `app/routes.py` | `create_bill` |
| 6 | `GET /api/bills/{id}` | `app/routes.py` | `get_bill` |
| 7 | `PATCH /api/bills/{id}/status` | `app/routes.py` | `patch_bill_status` |
| 8 | `GET /api/users/{id}/library` | `app/routes.py` | `get_library` |
| 9 | `GET /api/users/{id}` | `app/routes.py` | `get_user` |

Фабрика `create_app(db_path)` і lifespan (БД не створюється на імпорті): `app/main.py`.

## 2. SRC ЛР1 → реалізація ЛР2 → тести

| SRC | Що зроблено | Тести (файли) | Рядок матриці |
| --- | --- | --- | --- |
| SRC-02 | Product create/read + фільтри `q`∧`category` | `tests/test_products.py` | `CURRENT_LR2` у [traceability.csv](traceability.csv) |
| SRC-03 | Bill + BillItem, знімок ціни; 409 повторна покупка Paid/Completed | `tests/test_bills.py` | `CURRENT_LR2` |
| SRC-04 | Матриця статусів Bill, 409 без UPDATE | `tests/test_bills.py` | `CURRENT_LR2` |
| SRC-05 | Бібліотека Paid/Completed; чужа (у т.ч. Admin) → 403 | `tests/test_library.py` | `CURRENT_LR2` |
| SRC-06 | Admin/User seed; профіль лише власнику; `X-User-Id` | `test_products.py`, `test_bills.py`, `test_users.py` | `CURRENT_LR2` |
| SRC-01 / SRC-07 | Поза обсягом ЛР2 | — | — |

## 3. Сценарії T01–T14 (адаптовані до Product/Bill)

| ID | Сенс у Luden | Тест-функція | Файл |
| --- | --- | --- | --- |
| T01 | Мінімальне створення Product | `test_t01_create_minimal_body` | `tests/test_products.py` |
| T02 | Межі/trim назви | `test_t02_name_trim_boundaries` | `tests/test_products.py` |
| T03 | Список/деталі/404 | `test_t03_list_and_detail` | `tests/test_products.py` |
| T04 | Фільтр → порожній список | `test_t04_filter_category_empty` | `tests/test_products.py` |
| T05 | `q` + невідомий genre → `[]` | `test_t05_filter_query_and_unknown_category` | `tests/test_products.py` |
| T06 | AND двох фільтрів | `test_t06_and_filters` | `tests/test_products.py` |
| T07 | Частковий PATCH, null заборонено | `test_t07_partial_patch` | `tests/test_products.py` |
| T08 | Власник / чужий User 403 / Admin 200 | `test_t08_owner_and_foreign_access` | `tests/test_bills.py` |
| T09 | Дозволений перехід + повтор статусу | `test_t09_allowed_transition_and_repeat` | `tests/test_bills.py` |
| T10 | Заборонений перехід, стан збережено | `test_t10_forbidden_transition_preserves_status` | `tests/test_bills.py` |
| T11 | Валідація позицій Bill | `test_t11_bill_items_validation` | `tests/test_bills.py` |
| T12 | Немає Product 404; бібліотека після Paid | `test_t12_missing_product_and_library_after_paid` | `tests/test_bills.py` |
| T13 | Збереження після «перезапуску» | `test_t13_persistence_across_restart` | `tests/test_products.py` |
| T14 | Порожній/unknown/immutable PATCH | `test_t14_empty_patch_unknown_and_immutable` | `tests/test_products.py` |

Додаткові (не замінюють T01–T14): ізоляція БД; атомарність Bill; `priceAtPurchase`; **25 клітинок** матриці §5; Admin read/PATCH чужого Bill; профіль (`test_users.py`); 409 repurchase Paid/**Completed**; бібліотека без Pending/Declined; multi-item total; `productIds` ≤0 → 422.

**Як перевірити локально:**

```bat
python -m pytest -q
python -m ruff check app tests --select E4,E7,E9,F,I
```

Очікувано: **67 passed**; Ruff — All checks passed.  
**CI:** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — pytest + ruff на `main` / PR. Локально — команди вище (див. [lab-02.md](lab-02.md)).

Зрізи **A–E**: `.agents/skills/tracker-slice/references/slices.md` (зріз E — профіль; зріз B — матриця 25; зріз C — repurchase/бібліотека).  
Експеримент: [experiments/protocol.md](../experiments/protocol.md).

## 4. Git-теги (фактичні peeled hashes)

Сторінка тегів: https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/tags

| Тег | Peeled commit | Що містить |
| --- | --- | --- |
| `lab02-skill-v0` | `git rev-parse lab02-skill-v0^{}` | Skill, зрізи A–D |
| `lab02-ai-draft` | `git rev-parse lab02-ai-draft^{}` | AI-патч зрізу B (`patches/`) |
| `lab02-implemented` | `git rev-parse lab02-implemented^{}` | Здавальна версія |

```bat
git fetch --all --tags
git rev-parse lab02-skill-v0^{}
git rev-parse lab02-ai-draft^{}
git rev-parse lab02-implemented^{}
git show lab02-implemented:.agents/skills/tracker-slice/references/slices.md
```

Повний AI-diff: [../patches/lab02-ai-draft-slice-b.patch](../patches/lab02-ai-draft-slice-b.patch)

## 5. Skill v0 → v1

| Версія | Де дивитись | Відмінність |
| --- | --- | --- |
| v0 | тег `lab02-skill-v0` / опис у ai-log | зріз B: schemas/services/routes |
| v1 | `references/slices.md` у дереві | для зрізу B: **не** змінювати `database.py`; відхилено `bill_events` |
| E | `references/slices.md` | профіль власника — уточнення після рев’ю доступу |

Копії Skill: `.agents/skills/tracker-slice/` і `.claude/skills/tracker-slice/`.

## 6. Ізоляція тестів від робочої БД

- `tests/conftest.py` — `create_app(db_path=tmp_path / "test.db")` + `TestClient` (lifespan).
- `app/main.py` — `init_db` лише в lifespan, не під час `import app.main`.
- Доказ: `tests/test_isolation.py`.
