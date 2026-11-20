# Лабораторна робота №2 — реалізація з AI-асистентом (Luden)

Команда: Паламарчук Антон, Татьков Олександр, Сергєєва Таісія, Панковський Тимофій.  
База: тег `lab01-spec-published` у [luden-ai-labs](https://github.com/NureTatkovOleksandr/luden-ai-labs); навчальний сервіс — цей репозиторій ([NureSerhiehievaTaisiia/luden-ai-lab2](https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2)).

## Мета й обсяг

Реалізовано навчальний REST API (FastAPI + SQLite) за правилами ЛР1 без зміни канону `requirements.md`. Предметна область — Luden (додаток Б методички + [methodology-crosswalk.md](methodology-crosswalk.md)), не Mini Issue Tracker. Поза обсягом: Stripe, Firebase, React UI, OAuth, SRC-07.

Тема Luden (додаток Б) узгоджена з викладачем до тегу `lab02-skill-v0`. Письмового листа в репозиторії немає; підтвердження — усне / на занятті. Обґрунтування адаптації: [methodology-crosswalk.md](methodology-crosswalk.md).

`X-User-Id` — навчальна симуляція власника запиту, **не** автентифікація (не JWT / OAuth).

## Внесок команди

| Учасник | Зона відповідальності в ЛР2 |
| --- | --- |
| Сергєєва Таісія | Skill `tracker-slice`, зріз B (статуси Bill), репозиторій GitHub, фінальна збірка здавання |
| Паламарчук Антон | Тести каталогу T01–T07 / T13–T14, фільтри, ізоляція БД |
| Татьков Олександр | Тести Bill / бібліотека T08–T12, матриця статусів, права доступу |
| Панковський Тимофій | Мікроексперимент no-AI vs AI, рев’ю AI-diff, звіт `lab-02.md` / acceptance-map |

На захисті всі четверо відповідають на контрольні питання методички (с. 10).

## Реалізовані FR / SRC

| SRC | Результат у ЛР2 | Тести |
| --- | --- | --- |
| SRC-02 | POST/GET Product, деталі, фільтри `q`∧`category` | `tests/test_products.py` |
| SRC-03 | Bill з унікальними productIds, quantity=1, знімок ціни; 409 на повторну покупку Paid/Completed | `tests/test_bills.py` |
| SRC-04 | Матриця статусів Bill (§5); 409 без зміни запису | `tests/test_bills.py` |
| SRC-05 | Бібліотека = DISTINCT Product з Paid/Completed; чужа бібліотека (у т.ч. Admin) → 403 | `tests/test_library.py` |
| SRC-06 | Seed User/Admin/User; Admin-only Product; профіль лише власнику; `X-User-Id` — симуляція | `tests/test_products.py`, `tests/test_bills.py`, `tests/test_users.py` |
| SRC-01/07 | Не реалізовано (як FR-08 у прикладі MIT) | — |

Навчальний wire: [lr2-api.md](lr2-api.md). Матриця: [traceability.csv](traceability.csv) (рядки `CURRENT_LR2`).  
Карта приймання: [acceptance-map-lr2.md](acceptance-map-lr2.md).

## Фактичні Git-теги та хеші

| Тег / подія | Commit (peeled) | Примітка |
| --- | --- | --- |
| `lab02-skill-v0` | `git rev-parse lab02-skill-v0^{}` | Skill tracker-slice, зрізи A–D у розбитті; docs ЛР1 |
| `lab02-ai-draft` | `git rev-parse lab02-ai-draft^{}` | AI-патч зрізу B (повний diff у `patches/`) |
| Skill v1 | `.agents/skills/tracker-slice/references/slices.md` | Для зрізу B заборонено `database.py`; відхилено `bill_events` |
| `lab02-implemented` | `git rev-parse lab02-implemented^{}` | Здавальна версія (профіль E, repurchase, матриця 25, експеримент, CI) |

Зріз **E** (профіль власника) — уточнення після рев’ю доступу до профілю; базове розбиття A–D зафіксоване тегом `lab02-skill-v0`.

Повний AI-draft diff: [patches/lab02-ai-draft-slice-b.patch](../patches/lab02-ai-draft-slice-b.patch)  
Коротке рев’ю: [patches/lab02-ai-draft-review-uk.md](../patches/lab02-ai-draft-review-uk.md)

```bat
git fetch --all --tags
git rev-parse lab02-skill-v0^{} lab02-ai-draft^{} lab02-implemented^{}
git tag -n
```

## Skill: крок 0 і v0 → v1

| Запит | Очікування | Результат |
| --- | --- | --- |
| «Додай PATCH /api/bills/{id}/status за матрицею §5» | Skill | Так |
| «T10: Paid→Pending дає 200. Виправ» | Skill | Так |
| «Реалізуй бібліотеку користувача після Paid» | Skill | Так |
| «Поясни різницю 409 і 422» | Ні | Ні |
| «Онови README: команди запуску» | Ні | Ні |
| «Як створити venv у Windows?» | Ні | Ні |

Після AI-draft уточнено v1: для зрізу B заборонено зайві зміни `database.py` (агент пропонував індекс/`bill_events`).

## AI-патч (зріз B)

- Запит: реалізувати переходи Bill і T09/T10 під Skill `tracker-slice`.
- Прийнято: матриця `ALLOWED_TRANSITIONS`, 409 без UPDATE, повтор статусу = 200.
- Змінено людиною: `sales_count` лише Processing→Paid; перевірка власника.
- Відхилено: `bill_events`, зайві правки схеми БД.
- Журнал: [ai-log.md](ai-log.md), [ai-log-lr2.md](ai-log-lr2.md).

## Тести та Ruff

```text
python -m pytest -q
python -m ruff check app tests --select E4,E7,E9,F,I
```

Локальний прогін 2026-11-20 (venv Python 3.14): `python -m pytest -q` → **67 passed**; `python -m ruff check app tests --select E4,E7,E9,F,I` → **All checks passed**. Покриті T01–T14, повна матриця §5 (25 клітинок), права Admin/User, атомарність Bill, знімок `priceAtPurchase`, фільтри, профіль (зріз E), бібліотека без неоплачених, 409 repurchase Paid/Completed, ізоляція від `data/app.db`. CI: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

`init_db` виконується лише в **lifespan** FastAPI: імпорт `app.main` не створює робочу БД; `TestClient` ініціалізує тимчасову базу.

Грошові суми в навчальному сервісі зберігаються як REAL/float; точне округлення в ЛР1 позначено OPEN (D-03) — окремих правил округлення не вигадано.

## Мікроексперимент AI / no-AI

Канон даних: [experiments/experiment-lr2.csv](../experiments/experiment-lr2.csv) і [experiments/protocol.md](../experiments/protocol.md). Файл `docs/experiment-lr2.csv` — лише покажчик на канон.

**Висновки для звіту:** пілот `matches_query` vs `matches_category` має різний принцип перевірки (підрядок vs exact) і **не** використовується для висновків про AI. Порівняльний ряд — співмірний повтор `equals_ci` (no-AI) / `role_equals_ci` (AI) з принципом isomorphic exact CI. Виконання `sequential-same-session`, n=1 — обмеження дизайну. Висновку «AI кращий» немає.

## AI-draft vs final

| Ризик | Перевірка |
| --- | --- |
| Заборонений перехід змінює статус | T10 + матриця Completed→Pending/Processing |
| Повторний Paid збільшує sales_count | окремий тест: sales_count лишається 1 |
| Частковий Bill при 404 | атомарність: COUNT bills/items не змінюється |
| Тести на робочій БД | conftest → `tmp_path` |

## Демонстрація захисту (Luden)

1. Чистий venv + `pip install -r requirements-lock.txt` (Python **3.14.0**)
2. `uvicorn` → Product (Admin) → Bill (User) → Processing → Paid → library
3. Paid→Pending → 409; повторна покупка Paid → 409; carol/Admin → чужий профіль/бібліотека → 403; фільтри; перезапуск
4. `pytest` + `ruff`; Skill v0/v1; `patches/lab02-ai-draft-slice-b.patch`

## Обмеження

Продуктовий ASP.NET / React / Firebase не змінювався. Навчальний сервіс ЛР2 — окремий FastAPI+SQLite.
