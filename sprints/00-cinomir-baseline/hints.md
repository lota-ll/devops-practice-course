# Спринт 00: підказки

Відкривай, якщо застряг на задачі більш ніж на 30–40 хвилин. Підказки йдуть від загальної до конкретної — зупинись, щойно стане зрозуміло, що робити далі. Готового коду тут немає, він у [solution/](solution/).

---

## Задача 1

<details><summary>1. З чого почати структуру</summary>

`src/`-layout (`src/cinomir/`) захищає від випадкового імпорту пакета з робочої директорії замість встановленого. Для pytest додай `pythonpath = ["src"]` у `[tool.pytest.ini_options]`, щоб тести працювали без встановлення пакета.
</details>

<details><summary>2. Як зробити <code>make help</code> без ручного списку</summary>

Коментар `## опис` після імені цілі + `grep` по `$(MAKEFILE_LIST)` + `awk` з роздільником `:.*?## `. `.DEFAULT_GOAL := help` — щоб `make` без аргументів показував довідку.
</details>

<details><summary>3. Конфігурація</summary>

Один клас налаштувань, створюється з оточення один раз (`functools.lru_cache`). `frozen=True` — щоб ніхто не змінив налаштування під час роботи. Список Telegram id — `frozenset[int]` з рядка через кому. Для тестів — `dataclasses.replace(settings, …)`, а не monkeypatch оточення.
</details>

<details><summary>4. gitleaks у pre-commit</summary>

У gitleaks є правило для токенів Telegram — воно спрацьовує, коли поруч є слово на кшталт `telegram`. Перевір свій хук на тестовому файлі **до** того, як покладатися на нього.
</details>

---

## Задача 2

<details><summary>1. Чому <code>Numeric</code>, а не <code>Float</code> для ціни</summary>

`0.1 + 0.2 != 0.3` у float. Для грошей — `Numeric(10, 2)` у БД і `Decimal` у Python (або float лише на виході в JSON).
</details>

<details><summary>2. Один URL для async-застосунку і sync-Alembic</summary>

psycopg 3 — один драйвер з двома режимами. `postgresql+psycopg://…` працює і з `create_async_engine`, і з `engine_from_config`. Не потрібні окремі `asyncpg` + `psycopg2`.
</details>

<details><summary>3. BIGINT і SQLite</summary>

SQLite робить autoincrement лише для `INTEGER PRIMARY KEY`. Для `price_snapshots.id` (а знімків буде багато → BIGINT у PostgreSQL) використай `BigInteger().with_variant(Integer(), "sqlite")`.
</details>

<details><summary>4. Як перевірити, що модель і міграції збігаються</summary>

`alembic check` порівнює метадані моделей зі станом БД після міграцій. Якщо щось не збігається — ненульовий код виходу. Це і є крок CI.
</details>

---

## Задача 3

<details><summary>1. Як дізнатися формат відповіді мережі</summary>

У тебе вже є `spike.py` і збережені відповіді. Для нових полів — DevTools → Network → Fetch/XHR на сайті мережі під час пошуку. Збережи 2–3 реальні елементи як зразки для тестів (`tests/samples.py`).
</details>

<details><summary>2. Як тестувати HTTP без мережі</summary>

`httpx.MockTransport(handler)` — функція отримує `httpx.Request` і повертає `httpx.Response`. Один обробник на всі три хости, з лічильником викликів і перемикачами «ця мережа повертає 500 / Cloudflare» — і ти можеш тестувати деградацію.
</details>

<details><summary>3. Наявність по мережах</summary>

Сільпо: `stock` (кількість). Фора: `quantity` (0 = «немає в наявності» на сайті). Novus: лише прапорець `in_stock`. Якщо мережа нічого не каже — `None`, а не `True`: «не знаємо» ≠ «є».
</details>

<details><summary>4. GTIN: чому 14 цифр і що з кодами 02x</summary>

GTIN-14 з провідним нулем = той самий GTIN-13. GTIN-14 з першою цифрою 1–8 — код **ящика**; одиничний товар з нього можна вивести (прибрати першу цифру, перерахувати контрольну), але позначити як `from_case`. Префікси `020–029` — внутрішні коди магазину (вагові товари), для зіставлення між мережами непридатні.
</details>

<details><summary>5. Релевантність</summary>

Токени ≥ 3 символів, порівняння за префіксом (гасить відмінки: «соку»/«соці»). Перше слово запиту — обов'язкове. Перед порівнянням заміни латинські `i a e o c p x` на кириличні — в назвах товарів таке трапляється.
</details>

---

## Задача 4

<details><summary>1. Таймаут на кожну мережу, а не на весь пошук</summary>

`asyncio.gather(*(fetch(c) for c in chains))`, а всередині `fetch` — `asyncio.wait_for(chain.search(...), timeout)`. Кожен `fetch` сам ловить свої винятки і повертає статус — тоді `gather` ніколи не падає цілком.
</details>

<details><summary>2. Чому таймаут HTTP-клієнта більший за таймаут мережі</summary>

Якщо клієнт httpx має той самий таймаут, він іноді спрацює першим, і в статусі буде `ConnectTimeout` замість зрозумілого «не відповіла вчасно». Зроби таймаут клієнта трохи більшим — керує `wait_for`.
</details>

<details><summary>3. Upsert без діалектних хитрощів</summary>

Вибери наявні товари за `chain_product_id IN (...)`, відфільтруй пари `(chain, id)` у Python, створи відсутні, `flush()` — нові отримають `id`, потім додай знімки за `product_id`. Працює однаково на SQLite і PostgreSQL. Не використовуй `product.snapshots.append()` в async — це ліниве завантаження.
</details>

<details><summary>4. Зіставлення товарів</summary>

Union-find: для кожної пропозиції ключі `ean:<код>` і (для Сільпо/Фори) `fozzy:<id>`. Пропозиції зі спільним ключем об'єднуються. Група цікава, лише якщо в ній ≥ 2 різні мережі.
</details>

<details><summary>5. Шаблон маршруту в middleware</summary>

Після `call_next` у `request.scope["route"]` лежить об'єкт маршруту, `.path` — шаблон на кшталт `/api/v1/search/{search_id}`. Для неіснуючих шляхів маршруту немає — підстав `unmatched`.
</details>

<details><summary>6. Як тестувати API разом з lifespan</summary>

`httpx.ASGITransport` не запускає lifespan. Обгорни клієнт у `async with app.router.lifespan_context(app):`. Фабрика `create_app(settings, http=…, redis=…)` дозволяє підсунути MockTransport і fakeredis.
</details>

---

## Задача 5

<details><summary>1. Graceful shutdown воркера</summary>

`loop.add_signal_handler(SIGTERM, stop_event.set)`, цикл `while not stop.is_set()`, `BRPOP` з таймаутом 1–2 с. Паузи — через `wait_for(stop.wait(), timeout)`, щоб SIGTERM переривав і їх.
</details>

<details><summary>2. Дедуплікація черги</summary>

`SADD pending id` повертає 1, лише якщо id ще не було в множині → тоді `LPUSH`. Воркер робить `SREM` у `finally`. А щоб не питати Сільпо щоразу про товар без штрихкоду — запам'ятовуй час перевірки в БД.
</details>

<details><summary>3. Allowlist в aiogram</summary>

Outer middleware на `dp.message` і `dp.callback_query`. Користувач — у `data["event_from_user"]`. Не викликати `handler` = подія не обробляється.
</details>

<details><summary>4. Кнопки і обмеження Telegram</summary>

`callback_data` ≤ 64 байт: `p:<search_id 16 символів>:<сторінка>:<сортування>` — вміщається. Повідомлення ≤ 4096 символів: 8 товарів на сторінку з запасом. `link_preview_is_disabled=True` у `DefaultBotProperties`, інакше Telegram додасть прев'ю першого посилання.
</details>

---

## Задача 6

<details><summary>1. Кеш шару залежностей без копіювання <code>src/</code></summary>

Скопіюй лише `pyproject.toml`, витягни список залежностей (`tomllib`) у `requirements.txt`, встанови. Потім копіюй `src/` і `pip install --no-deps .`. Зміна коду не інвалідує шар залежностей.
</details>

<details><summary>2. Порядок старту в Compose</summary>

`depends_on` з умовами: `service_healthy` (postgres, redis), `service_completed_successfully` (migrate). Бот — `profiles: ["bot"]`, щоб `make up` не вимагав токена.
</details>

<details><summary>3. Healthcheck без curl</summary>

У `python:*-slim` немає curl. Використай `python -c "import urllib.request …"`. Для воркера і бота HTTP-ендпоінта на 8000 немає — вимкни для них успадкований healthcheck (`healthcheck: disable: true`).
</details>

---

## Задача 7

<details><summary>1. PostgreSQL у GitHub Actions</summary>

`services:` у job з `options: --health-cmd "pg_isready …"` — Actions чекає healthy перед кроками. Порт пробрось на `localhost`.
</details>

<details><summary>2. Образ для Trivy без push</summary>

`docker/build-push-action` з `load: true` кладе образ у локальний Docker раннера. Сканування і smoke-тест — до push.
</details>

<details><summary>3. Які версії actions брати</summary>

Не `@master` і не `latest`. У березні 2026 теги `aquasecurity/trivy-action` 0.0.1–0.34.2 були підмінені шкідливими комітами ([GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23)). Мінімум — безпечна версія з immutable release; повний пін за SHA — у спринті 08.
</details>

<details><summary>4. Промоут з approve</summary>

Settings → Environments → `staging` → Required reviewers. У job — `environment: staging`. Retag без перезбирання: `docker buildx imagetools create -t …:staging …:sha-xxxxxxx`. Ім'я образу в GHCR — лише малими літерами.
</details>

<details><summary>5. Образ для Raspberry Pi (arm64)</summary>

`docker/setup-qemu-action` + `platforms: linux/amd64,linux/arm64` у `build-push-action` з `push: true`. `load: true` з кількома платформами не працює (класичне сховище Docker тримає одну архітектуру на тег) — тому перевірки й Trivy робимо на amd64, а мультиархітектурну збірку — окремим кроком із тим самим кешем. Базові образи `python:3.13-slim`, `postgres`, `redis` і колеса `psycopg[binary]` уже мають arm64.
</details>
