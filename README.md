# Luden — ЛР 2: реалізація з AI-асистентом

Навчальний REST-сервіс за специфікацією ЛР1 команди Luden ([docs/requirements.md](docs/requirements.md)), стек ЛР2: **FastAPI + SQLite + pytest**.

- Репозиторій ЛР2: https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2  
- Специфікація ЛР1: https://github.com/NureTatkovOleksandr/luden-ai-labs  

### Проєкт Luden (до якого виконувалась лабораторна)

| Частина | Репозиторій |
| --- | --- |
| Backend | https://github.com/NurePalamarchukAnton/Luden-Back-End |
| Frontend | https://github.com/NurePalamarchukAnton/Luden-Front-End |

Домен Luden збережено (додаток Б методички / [methodology-crosswalk.md](docs/methodology-crosswalk.md)): Product / Bill / бібліотека. Навчальний FastAPI-сервіс ЛР2 не замінює продуктовий ASP.NET / React стек.

## Документи здавання

| Файл | Зміст |
| --- | --- |
| [docs/acceptance-map-lr2.md](docs/acceptance-map-lr2.md) | **Карта приймання:** 9 маршрутів, T01–T14→функції тестів, SRC, теги, Skill v0/v1 |
| [docs/lab-02.md](docs/lab-02.md) | Звіт ЛР2, хеші тегів, AI-патч |
| [docs/ai-log.md](docs/ai-log.md) §10 | AI-журнал реалізації ЛР2 |
| [experiments/protocol.md](experiments/protocol.md) | Протокол мікроексперименту AI / no-AI |
| [experiments/experiment-lr2.csv](experiments/experiment-lr2.csv) | Результати (пілот + співмірний повтор) |
| [docs/lr2-api.md](docs/lr2-api.md) | Навчальний API-контракт |
| [docs/traceability.csv](docs/traceability.csv) | Матриця + рядки `CURRENT_LR2` |

### Як перевірити заяви README (не на слово)

| Заява | Де підтвердити на GitHub / локально |
| --- | --- |
| 9 маршрутів + `/health` | [`app/routes.py`](app/routes.py) · таблиця в [acceptance-map-lr2.md](docs/acceptance-map-lr2.md) |
| T01–T14 | імена `test_t01`…`test_t14` у [`tests/`](tests/) · карта T-id |
| Тимчасова БД | [`tests/conftest.py`](tests/conftest.py) + [`tests/test_isolation.py`](tests/test_isolation.py); `init_db` у lifespan [`app/main.py`](app/main.py) |
| Три теги | https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/tags |
| Skill v0 → v1 | [`.agents/skills/tracker-slice/references/slices.md`](.agents/skills/tracker-slice/references/slices.md) |
| AI-draft | [`patches/lab02-ai-draft-slice-b.patch`](patches/lab02-ai-draft-slice-b.patch) |
| SRC-02…SRC-06 | [traceability.csv](docs/traceability.csv) рядки `CURRENT_LR2` · [lab-02.md](docs/lab-02.md) |

## Вимоги до середовища

- **Python 3.14.0** (зафіксовано в локальному `.venv`; сумісність з 3.11+ очікувана, але здавання перевірялось на 3.14.0)
- Windows / macOS / Linux

## Встановлення

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

PowerShell без активації:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

## Запуск API

```bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health  
- Swagger: http://127.0.0.1:8000/docs  
- БД: `data/app.db` (не комітиться)  
- Заголовок: `X-User-Id: 1` (alice, User), `2` (bob, Admin), `3` (carol, User) — **симуляція, не JWT**

### Приклади запитів

```http
POST /api/products
X-User-Id: 2
Content-Type: application/json

{"name":"Cyber Quest","price":29.99,"category":"rpg"}
```

```http
POST /api/bills
X-User-Id: 1
Content-Type: application/json

{"productIds":[1]}
```

```http
PATCH /api/bills/1/status
X-User-Id: 1
Content-Type: application/json

{"status":"Processing"}
```

### HTTP-коди

| Код | Коли |
| --- | --- |
| 200 | Читання / успішне оновлення / повтор того самого статусу |
| 201 | Створення Product або Bill |
| 401 | Немає / невідомий `X-User-Id` |
| 403 | Немає права (не Admin / чужий ресурс) |
| 404 | Немає Product/Bill |
| 409 | Заборонений перехід статусу або повторна покупка Paid/Completed |
| 422 | Невалідні дані / unknown fields / null у заборонених полях |

## Тести та лінт

```bat
python -m pytest -q
python -m ruff check app tests --select E4,E7,E9,F,I
```

Очікувано після доведення: **67 passed**; Ruff — All checks passed.  
Тести використовують тимчасову БД (`tmp_path`), не `data/app.db`.  
CI: `.github/workflows/ci.yml` (pytest + ruff на push/PR до `main`).

### Швидка перевірка API після запуску

1. `GET /health` → `{"status":"ok"}`
2. Admin (`X-User-Id: 2`) створює Product → 201
3. User (`X-User-Id: 1`) створює Bill → Processing → Paid → `GET /api/users/1/library` містить гру
4. Повторний Bill тієї ж гри → 409; `GET /api/users/3` з заголовком Alice → 403
5. Перезапуск uvicorn — Product лишається в `data/app.db`

## Skill tracker-slice

```text
.agents/skills/tracker-slice/SKILL.md
.agents/skills/tracker-slice/references/slices.md
.claude/skills/tracker-slice/   (копія для Claude Code)
```

- **v0:** тег [`lab02-skill-v0`](https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/releases/tag/lab02-skill-v0)  
- **v1:** у дереві Skill — для зрізу B заборонено зайві зміни `database.py` / `bill_events`  
- AI-draft: [patches/lab02-ai-draft-slice-b.patch](patches/lab02-ai-draft-slice-b.patch)

## Git-теги

Сторінка: https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/tags

| Тег | Commit (peeled) |
| --- | --- |
| [lab02-skill-v0](https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/releases/tag/lab02-skill-v0) | `git rev-parse lab02-skill-v0^{}` |
| [lab02-ai-draft](https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/releases/tag/lab02-ai-draft) | `git rev-parse lab02-ai-draft^{}` |
| [lab02-implemented](https://github.com/NureSerhiehievaTaisiia/luden-ai-lab2/releases/tag/lab02-implemented) | `git rev-parse lab02-implemented^{}` |

```bat
git fetch --all --tags
git tag -n
git rev-parse lab02-skill-v0^{} lab02-ai-draft^{} lab02-implemented^{}
```

## Структура

```text
.agents/skills/tracker-slice/   Skill (A–E)
.claude/skills/tracker-slice/   копія Skill
.github/workflows/ci.yml        pytest + ruff
app/                            FastAPI
tests/                          T01–T14 + матриця/негативи
docs/                           ЛР1 + звіт ЛР2
experiments/                    протокол і CSV AI/no-AI
patches/                        AI-draft
data/                           локальна БД
```

## Обсяг SRC (ЛР1 → ЛР2)

| SRC | У ЛР2 |
| --- | --- |
| SRC-02…SRC-06 | Реалізовано (каталог, Bill, статуси, бібліотека, ролі-симуляція) |
| SRC-01, SRC-07 | Поза обсягом (як FR-08 у прикладі MIT) |

Деталі: [acceptance-map-lr2.md](docs/acceptance-map-lr2.md), рядки `CURRENT_LR2` у [traceability.csv](docs/traceability.csv).

## Навчальні обмеження

- Немає Stripe / Firebase / React UI / OAuth  
- `X-User-Id` ≠ автентифікація  
- SRC-01 / SRC-07 і хмара поза ЛР2  

## Команда

Паламарчук Антон, Татьков Олександр, Сергєєва Таісія, Панковський Тимофій.
