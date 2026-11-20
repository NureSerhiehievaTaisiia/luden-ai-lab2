# Навчальний API ЛР 2 (FastAPI + SQLite)

Версія: lab02. Це **навчальна прив’язка** правил ЛР1 ([requirements.md](requirements.md), [api-contract.md](api-contract.md)) до локального сервісу. Канон бізнес-правил не змінюється. Stripe, Firebase, JWT і React UI **поза обсягом** ЛР2; власник передається заголовком `X-User-Id` (навчальна симуляція, не автентифікація).

## Загальні правила

| Тема | Правило |
| --- | --- |
| База | SQLite-файл; дані переживають перезапуск |
| Seed | Три користувачі: `1` User (`alice`), `2` Admin (`bob`), `3` User (`carol`); повторна ініціалізація не дублює |
| JSON | camelCase у відповідях; вхід — snake_case або camelCase (Pydantic aliases) |
| Невідомі поля | `extra=forbid` → 422 |
| Помилки | `{ "detail": "..." }` або ValidationProblem; без SQL/traceback/шляхів |
| Коди | 201 create; 200 read/update; 404 відсутній ресурс; 409 заборонений перехід/конфлікт; 422 невалідні дані |

## Маршрути (9 бізнес + health)

| # | Метод | Шлях | Опис |
| --- | --- | --- | --- |
| 0 | GET | `/health` | `{"status":"ok"}` |
| 1 | POST | `/api/products` | Створити Product (лише Admin, `X-User-Id: 2`) |
| 2 | GET | `/api/products` | Список; опційно `q`, `category` (AND) |
| 3 | GET | `/api/products/{id}` | Деталі |
| 4 | PATCH | `/api/products/{id}` | Presence-aware PATCH (Admin) |
| 5 | POST | `/api/bills` | Створити Bill зі знімком цін (User) |
| 6 | GET | `/api/bills/{id}` | Деталі Bill + items; власник або Admin |
| 7 | PATCH | `/api/bills/{id}/status` | Перехід за матрицею §5; власник або Admin |
| 8 | GET | `/api/users/{id}/library` | Product з власних Paid/Completed; лише власник (`X-User-Id`); Admin чужу не читає |
| 9 | GET | `/api/users/{id}` | Профіль seed; лише власник (`X-User-Id`); чужий → 403; немає → 404 |

## Product

**Create** (`name` обов’язковий після trim, довжина 3..200; `description` default `""`; `price` ≥ 0.01; `stock` ≥ 0; `category` default `""`; клієнт не задає `id`/`createdAt`/`salesCount`).

**PATCH**: змінює лише передані поля; `name`/`price`/`stock` null → 422; порожній `{}` → 422; unknown → 422; жодна часткова зміна при помилці.

**Список**: порядок `id ASC`. Фільтри разом — AND.

| Параметр | Відсутній у query | Переданий, але порожній після trim (`q=` / `category=`) | Ненульове значення |
| --- | --- | --- | --- |
| `q` | не фільтрувати | не фільтрувати (як відсутній) | case-insensitive substring по `name` |
| `category` | не фільтрувати | не фільтрувати (як відсутній) | точний збіг case-insensitive |

Порожній параметр **не** дає 422: для вільного рядка `category` це узгоджена навчальна поведінка (не enum). Невідоме непорожнє значення жанру → `200` і `[]`.

## Bill

**Create body**: `{ "productIds": [1, 2] }` — непорожній, унікальні id, Product існує, quantity=1, `priceAtPurchase` = поточна `Product.price`, `totalAmount` = сума, `status=Pending`, `currency=UAH`, `userId` з `X-User-Id`. Якщо будь-який Product уже є в власних Bill зі статусом `Paid` або `Completed` — `409` (повторна покупка заборонена; `Declined` не блокує).

**Статуси (wire)**: `Pending`, `Processing`, `Declined`, `Paid`, `Completed`.

Матриця (Д / Т / Н) — як у requirements §5 (5×5 = 25 комбінацій). Т (той самий статус) → 200 без зміни даних. Н → 409, запис не змінюється.

**Права Bill:** власник (`X-User-Id` = `userId`) читає й змінює статус; **Admin** також може читати будь-який Bill і виконувати дозволені переходи (навчальна симуляція підтримки). Звичайний чужий User → 403. Профіль і бібліотека **не** мають Admin-override (лише власник).

Навчальна симуляція оплати: перехід `Processing → Paid` одразу фіксує право (без Stripe) і збільшує `salesCount`. `Paid → Completed` — завершення доставки (no-op для ключів у ЛР2).

## Бібліотека

DISTINCT Product з BillItem власних Bill у статусі `Paid` або `Completed`. Порожній список → `[]` і 200. Чужий `id` у path при невідповідності `X-User-Id` → 403.

## Поза обсягом ЛР2

Firebase, Stripe, OAuth, бонуси, favorites, cover upload, soft-delete Product, server Cart як окремий ресурс, FR/SRC-07 (скидання пароля).
