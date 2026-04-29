# OLX API Parser Bot

Telegram-бот для парсинга объявлений с OLX.uz, сохранения их в базу данных и отправки отчётов.

## Содержание

- [Возможности](#возможности)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Команды бота](#команды-бота)
- [Архитектура](#архитектура)
- [Парсинг](#парсинг)
- [Вебхуки](#вебхуки)
- [Тестирование](#тестирование)
- [Утилиты](#утилиты)
- [Структура проекта](#структура-проекта)
- [Миграции](#миграции)

---

## Возможности

- ✅ Парсинг категорий OLX.uz (товары, цены, локация, параметры)
- ✅ Сохранение данных в PostgreSQL через SQLAlchemy ORM (асинхронно)
- ✅ Отчёт в формате Excel
- ✅ Отправка данных через вебхуки (outbox pattern)
- ✅ Планировщик задач (APScheduler)
- ✅ Устойчивые селекторы с fallback (защита от изменений вёрстки)
- ✅ Админ-панель для управления пользователями
- ✅ Валидация конфигурации через pydantic-settings
- ✅ Управление HTTP клиентом с корректным закрытием ресурсов

---

## Установка

### Требования

- Python 3.11+
- PostgreSQL 14+

### Шаг 1: Клонирование

```bash
git clone <repository-url>
cd olx_api
```

### Шаг 2: Виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка базы данных

Создайте базу данных PostgreSQL и обновите `.env` файл (см. раздел [Конфигурация](#конфигурация)).

### Шаг 5: Миграции

```bash
alembic upgrade head
```

---

## Конфигурация

Создайте файл `.env` в корне проекта:

```env
# База данных (обязательно)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Telegram бот (обязательно)
TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Админы (через запятую, @username или tg_id)
ADMINS=@username1,@username2,123456789

# Вебхуки (опционально)
WEBHOOK_URL=https://your-webhook-url.com/endpoint
WEBHOOK_TIMEOUT_SECONDS=10

# Планировщик (опционально)
SCHEDULE_CATEGORY_ID=/nedvizhimost/
SCHEDULE_CATEGORY_NAME=Недвижимость
PARSE_SCHEDULE_TIME=09:00
TELEGRAM_CHAT_ID=123456789

# Парсинг (опционально)
MAX_CONCURRENT_REQUESTS=5
BATCH_SIZE=200

# Очистка устаревших записей (0/1)
CLEANUP_MISSING=1
```

**Примечание:** Все обязательные поля валидируются при запуске через pydantic-settings. Если какое-то обязательное поле отсутствует, бот не запустится с понятной ошибкой.

---

## Использование

### Запуск бота

```bash
python aiogram_run.py
```

### Запуск парсера вручную

```bash
python db_handler/main.py
```

### Запуск тестов

```bash
pytest
```

---

## Команды бота

### Пользовательские команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкции |
| `/parse` | Запустить парсинг категории |
| `/report` | Получить отчёт в Excel |
| `/latest [N]` | Последние N объявлений (по умолчанию 10) |
| `/filters` | Информация о фильтрах |

### Админские команды

| Команда | Описание |
|---------|----------|
| `/add_admin @username` | Добавить админа |
| `/ban @username [причина]` | Забанить пользователя |
| `/unban @username` | Разбанить пользователя |
| `/stats` | Статистика бота |
| `/users` | Список пользователей |
| `/del_user @username` | Удалить пользователя |
| `/del_user_id <tg_id>` | Удалить по ID |
| `/allow_all` | Разрешить доступ всем |
| `/deny_all` | Запретить доступ всем |
| `/whoami` | Информация о текущем пользователе |

---

## Архитектура

### Технологический стек

- **Aiogram 3.x** — асинхронный фреймворк для Telegram ботов
- **SQLAlchemy 2.x** — ORM для работы с PostgreSQL
- **Alembic** — миграции базы данных
- **APScheduler** — планировщик задач
- **httpx** — асинхронный HTTP клиент
- **pydantic-settings** — валидация конфигурации
- **BeautifulSoup4** — парсинг HTML

### Структура директорий

```
olx_api/
├── config.py               # Централизованная конфигурация (pydantic-settings)
├── aiogram_run.py          # Точка входа бота
├── create_bot.py           # Создание бота и диспетчера
├── db_handler/             # Работа с БД
│   ├── main.py             # Парсинг и функции БД
│   ├── http_client.py      # Lifecycle manager для HTTP клиента
│   ├── services/           # Сервисы
│   │   ├── repository.py   # CRUD операции (SQLAlchemy)
│   │   ├── persistense.py  # Bulk insert через SQLAlchemy
│   │   ├── outbox_service.py      # Добавление в очередь вебхуков
│   │   ├── outbox_processor.py    # Обработка очереди вебхуков
│   │   └── webhook_serializer.py  # Сериализация для вебхуков
│   ├── db/                 # Модели и движок БД
│   │   ├── models.py       # SQLAlchemy модели (Product, User, Settings, WebhookOutbox)
│   │   └── engine.py       # Async/sync engine, SessionLocal
│   └── scheduler/          # Планировщик задач
│       └── outbox_scheduler.py
├── parser/                 # Парсинг OLX
│   ├── selectors.py        # Конфигурация селекторов
│   ├── selector_utils.py   # Утилиты поиска с fallback
│   ├── normalizer.py       # Нормализация данных
│   └── main_parser.py      # Основной парсер
├── handlers/               # Обработчики команд
│   └── start.py            # Команды бота
├── middlewares/            # Промежуточное ПО
│   └── db_session.py       # Middleware для инъекции SQLAlchemy сессии
├── filters/                # Фильтры сообщений
│   └── is_admin.py         # Фильтр проверки прав админа
├── keyboards/              # Inline-клавиатуры
├── export/                 # Экспорт данных (Excel)
├── utils/                  # Утилиты
│   └── exceptions.py       # Типы исключений для обработки ошибок
├── scripts/                # Скрипты утилит
├── alembic/                # Миграции Alembic
│   └── versions/           # Файлы миграций
└── tests/                  # Тесты pytest
```

### Ключевые компоненты

#### База данных (SQLAlchemy ORM)

Все операции с БД выполняются через SQLAlchemy ORM:
- **AsyncSession** — асинхронные сессии для всех операций
- **Bulk insert** — через `insert().on_conflict_do_update()` для производительности
- **Миграции** — через Alembic для версионирования схемы

#### HTTP клиент

- Глобальный `httpx.AsyncClient` управляется через lifecycle manager
- Семафор ограничивает одновременные запросы (по умолчанию 5)
- Корректное закрытие при shutdown бота

#### Middleware

`DbSessionMiddleware` автоматически создает SQLAlchemy сессию для каждого handler'а и передает её через `data["session"]`.

#### Outbox Pattern

Надежная доставка вебхуков:
1. События сохраняются в `webhook_outbox` таблицу
2. Фоновый процесс (каждые 15 сек) обрабатывает очередь
3. Exponential backoff при ошибках
4. Статусы: PENDING → SENT/FAILED/DEAD

---

## Парсинг

### Устойчивые селекторы

Парсер использует **fallback-селекторы** для устойчивости к изменениям вёрстки:

1. **data-testid** (приоритет 1) — стабильные атрибуты
2. **CSS классы** (приоритет 2) — могут меняться
3. **Семантические селекторы** (приоритет 3) — теги

### Найденные селекторы

#### Страница категории

| Элемент | data-testid | CSS класс |
|---------|-------------|-----------|
| Контейнер списка | `listing-grid` | `css-j0t2x2` |
| Карточка товара | `l-card` | `css-1sw7q4x` |
| Заголовок | `ad-card-title` | `css-u2ayx9` |
| Цена | `ad-price` | `css-blr5zl` |
| Локация | `location-date` | `css-3cz5o2` |
| Пагинация | `pagination-list` | — |

### Обновление селекторов

Если сайт изменился:

```bash
# 1. Исследовать новую структуру
python scripts/research_selectors.py

# 2. Обновить parser/selectors.py

# 3. Протестировать
python scripts/test_selectors.py
```

---

## Вебхуки

### Отправка данных

Данные отправляются через **outbox pattern**:

1. Данные сохраняются в таблицу `webhook_outbox`
2. Фоновый процесс (каждые 15 сек) отправляет данные
3. При ошибке — повторные попытки (exponential backoff)

### Обновление webhook URL

Если обновили `WEBHOOK_URL` в `.env`:

```bash
# Очистить очередь старых вебхуков
python scripts/clear_webhook_queue.py
```

---

## Тестирование

### Запуск всех тестов

```bash
pytest
```

### Запуск с покрытием

```bash
pytest --cov=. --cov-report=html
```

### Запуск конкретных тестов

```bash
pytest tests/test_selectors.py -v
pytest tests/test_webhook_serializer.py -v
```

### Структура тестов

```
tests/
├── conftest.py              # Фикстуры
├── test_selectors.py        # Тесты селекторов
├── test_selector_utils.py   # Тесты утилит поиска
├── test_webhook_serializer.py # Тесты сериализации
├── test_latest_handler.py   # Тесты /latest handler
└── test_parser.py           # Тесты парсера
```

---

## Утилиты

### `scripts/research_selectors.py`

Исследует структуру OLX.uz и находит стабильные селекторы.

**Использование:**
```bash
python scripts/research_selectors.py
```

**Результат:**
- `research_main_page.html` — главная страница
- `research_category_page.html` — страница категории
- `research_product_page.html` — страница товара

### `scripts/clear_webhook_queue.py`

Очищает очередь pending вебхуков из БД.

**Использование:**
```bash
python scripts/clear_webhook_queue.py
```

---

## Структура проекта

### База данных

#### Таблица `products`

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | ID записи |
| title | String | Заголовок объявления |
| price | Float | Цена |
| currency | String | Валюта (UZS/USD) |
| location | String | Локация |
| precise_location | String | Точная локация |
| url | String | URL объявления (уникальный) |
| category | String | Категория |
| created_at | DateTime | Дата создания |

#### Таблица `webhook_outbox`

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | ID события |
| target_url | String | URL вебхука |
| payload | JSON | Данные для отправки |
| status | Enum | PENDING/SENT/DEAD |
| attempts | Integer | Количество попыток |
| next_retry_at | DateTime | Следующая попытка |
| created_at | DateTime | Дата создания |

#### Таблица `users`

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | ID записи |
| tg_id | BigInteger | Telegram ID (поддержка больших ID) |
| username | String(255) | Username |
| is_admin | Boolean | Флаг админа |
| is_banned | Boolean | Флаг бана |
| ban_reason | Text | Причина бана |
| created_at | DateTime | Дата регистрации |

#### Таблица `settings`

| Поле | Тип | Описание |
|------|-----|----------|
| key | String(255) | Ключ настройки (PK) |
| value | Text | Значение настройки |

---

## Миграции

### Создание новой миграции

```bash
alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1

# Посмотреть текущую версию
alembic current

# История миграций
alembic history
```

### Важные миграции

- `41025f4c2198` — Регистрация существующих таблиц в Alembic
- `0d757a1f5c48` — Обновление модели User для BigInteger tg_id

### Основные модули

#### `config.py`

Централизованная конфигурация с валидацией через pydantic-settings:
- Автоматическая загрузка из `.env`
- Валидация обязательных полей при старте
- Type-safe доступ к настройкам

#### `db_handler/main.py`

Функции парсинга:
- `parse_products_from_category()` — парсинг списка товаров
- `parse_product_details()` — парсинг деталей товара
- `extract_products_links()` — извлечение ссылок
- `get_current_usd_rate()` — курс доллара

#### `db_handler/services/repository.py`

CRUD операции через SQLAlchemy:
- `list_latest_products()` — последние объявления
- `list_products_for_export()` — данные для экспорта
- `upsert_user()` — создание/обновление пользователя
- `get_user_by_tg_id()` — поиск по Telegram ID
- `mark_admin_by_username()` — назначение админа
- `set_ban_with_reason()` — бан пользователя

#### `db_handler/http_client.py`

Lifecycle manager для HTTP клиента:
- `get_http_client()` — получить глобальный клиент
- `close_http_client()` — закрыть клиент при shutdown

#### `parser/selectors.py`

Конфигурация селекторов:
- `CATEGORY_PAGE_SELECTORS` — для страницы категории
- `PRODUCT_PAGE_SELECTORS` — для страницы товара

#### `parser/selector_utils.py`

Утилиты:
- `find_with_fallback()` — поиск с fallback
- `get_text_fallback()` — извлечение текста
- `validate_selectors()` — валидация селекторов

#### `db_handler/services/outbox_service.py`

- `enqueue_webhook()` — добавить вебхук в очередь

#### `db_handler/services/outbox_processor.py`

- `process_outbox()` — обработка очереди (каждые 15 сек)
- `deliver_event()` — доставка одного события

#### `handlers/start.py`

Обработчики команд:
- `latest_command_handler()` — `/latest`
- `parse_command_handler()` — `/parse`
- `report_command_handler()` — `/report`
- Все админские команды

#### `middlewares/db_session.py`

Middleware для автоматической инъекции SQLAlchemy сессии в handlers.

#### `filters/is_admin.py`

Фильтр проверки прав администратора (создает собственную сессию, так как выполняется до middleware).

---

## Лицензия

MIT

---
