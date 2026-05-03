# OLX API Parser Bot

A Telegram bot for parsing product listings from OLX.uz, storing them in a database, and generating reports.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Bot Commands](#bot-commands)
- [Architecture](#architecture)
- [Parsing](#parsing)
- [Webhooks](#webhooks)
- [Testing](#testing)
- [Utilities](#utilities)
- [Project Structure](#project-structure)
- [Migrations](#migrations)

---

## Features

- ✅ Parse OLX.uz categories (products, prices, location, parameters)
- ✅ Store data in PostgreSQL via SQLAlchemy ORM (async)
- ✅ Generate Excel reports
- ✅ Send data via webhooks (outbox pattern)
- ✅ Task scheduler (APScheduler)
- ✅ Resilient selectors with fallback (protection against layout changes)
- ✅ Admin panel for user management
- ✅ Configuration validation via pydantic-settings
- ✅ HTTP client management with proper resource cleanup

---

## Installation

### Requirements

- Python 3.11+
- PostgreSQL 14+

### Step 1: Clone

```bash
git clone <repository-url>
cd olx_api
```

### Step 2: Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Database Setup

Create a PostgreSQL database and update the `.env` file (see [Configuration](#configuration) section).

### Step 5: Migrations

```bash
alembic upgrade head
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Database (required)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Telegram bot (required)
TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Admins (comma-separated, @username or tg_id)
ADMINS=@username1,@username2,123456789

# Webhooks (optional)
WEBHOOK_URL=https://your-webhook-url.com/endpoint
WEBHOOK_TIMEOUT_SECONDS=10

# Scheduler (optional)
SCHEDULE_CATEGORY_ID=/nedvizhimost/
SCHEDULE_CATEGORY_NAME=Real Estate
PARSE_SCHEDULE_TIME=09:00
TELEGRAM_CHAT_ID=123456789

# Parsing (optional)
MAX_CONCURRENT_REQUESTS=5
BATCH_SIZE=200

# Cleanup old records (0/1)
CLEANUP_MISSING=1
```

**Note:** All required fields are validated on startup via pydantic-settings. If any required field is missing, the bot will not start and will show a clear error message.

---

## Usage

### Run the bot

```bash
python aiogram_run.py
```

### Run the parser manually

```bash
python db_handler/main.py
```

### Run tests

```bash
pytest
```

---

## Bot Commands

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and instructions |
| `/parse` | Start parsing a category |
| `/report` | Get an Excel report |
| `/latest [N]` | Get last N listings (default 10) |
| `/filters` | Information about filters |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/add_admin @username` | Add an admin |
| `/ban @username [reason]` | Ban a user |
| `/unban @username` | Unban a user |
| `/stats` | Bot statistics |
| `/users` | List users |
| `/del_user @username` | Delete user |
| `/del_user_id <tg_id>` | Delete by ID |
| `/allow_all` | Allow access for everyone |
| `/deny_all` | Deny access for everyone |
| `/whoami` | Current user information |

---

## Architecture

### Technology Stack

- **Aiogram 3.x** — async framework for Telegram bots
- **SQLAlchemy 2.x** — ORM for PostgreSQL
- **Alembic** — database migrations
- **APScheduler** — task scheduler
- **httpx** — async HTTP client
- **pydantic-settings** — configuration validation
- **BeautifulSoup4** — HTML parsing

### Directory Structure

```
olx_api/
├── config.py               # Centralized configuration (pydantic-settings)
├── aiogram_run.py          # Bot entry point
├── create_bot.py           # Bot and dispatcher creation
├── db_handler/             # Database operations
│   ├── main.py             # Parsing and DB functions
│   ├── http_client.py      # HTTP client lifecycle manager
│   ├── services/           # Services
│   │   ├── repository.py   # CRUD operations (SQLAlchemy)
│   │   ├── persistense.py  # Bulk insert via SQLAlchemy
│   │   ├── outbox_service.py      # Webhook queue management
│   │   ├── outbox_processor.py    # Webhook queue processing
│   │   └── webhook_serializer.py  # Webhook serialization
│   ├── db/                 # Models and DB engine
│   │   ├── models.py       # SQLAlchemy models (Product, User, Settings, WebhookOutbox)
│   │   └── engine.py       # Async/sync engine, SessionLocal
│   └── scheduler/          # Task scheduler
│       └── outbox_scheduler.py
├── parser/                 # OLX parsing
│   ├── selectors.py        # Selector configuration
│   ├── selector_utils.py   # Fallback search utilities
│   ├── normalizer.py       # Data normalization
│   └── main_parser.py      # Main parser
├── handlers/               # Command handlers
│   └── start.py            # Bot commands
├── middlewares/            # Middleware
│   └── db_session.py       # SQLAlchemy session injection middleware
├── filters/                # Message filters
│   └── is_admin.py         # Admin rights filter
├── keyboards/              # Inline keyboards
├── export/                 # Data export (Excel)
├── utils/                  # Utilities
│   └── exceptions.py       # Exception types for error handling
├── scripts/                # Utility scripts
├── alembic/                # Alembic migrations
│   └── versions/           # Migration files
└── tests/                  # pytest tests
```

### Key Components

#### Database Layer (SQLAlchemy ORM)

All database operations are performed via SQLAlchemy ORM:
- **AsyncSession** — async sessions for all operations
- **Bulk insert** — via `insert().on_conflict_do_update()` for performance
- **Migrations** — via Alembic for schema versioning

#### HTTP Client

- Global `httpx.AsyncClient` managed via lifecycle manager
- Semaphore limits concurrent requests (default 5)
- Proper cleanup on bot shutdown

#### Middleware

`DbSessionMiddleware` automatically creates a SQLAlchemy session for each handler and passes it via `data["session"]`.

#### Outbox Pattern

Reliable webhook delivery:
1. Events are saved to `webhook_outbox` table
2. Background process (every 15s) processes the queue
3. Exponential backoff on errors
4. Statuses: PENDING → SENT/FAILED/DEAD

---

## Parsing

### Resilient Selectors

The parser uses **fallback selectors** for resilience against layout changes:

1. **data-testid** (priority 1) — stable attributes
2. **CSS classes** (priority 2) — can change
3. **Semantic selectors** (priority 3) — tags

### Found Selectors

#### Category Page

| Element | data-testid | CSS class |
|---------|-------------|-----------|
| List container | `listing-grid` | `css-j0t2x2` |
| Product card | `l-card` | `css-1sw7q4x` |
| Title | `ad-card-title` | `css-u2ayx9` |
| Price | `ad-price` | `css-blr5zl` |
| Location | `location-date` | `css-3cz5o2` |
| Pagination | `pagination-list` | — |

### Updating Selectors

If the site changes:

```bash
# 1. Research new structure
python scripts/research_selectors.py

# 2. Update parser/selectors.py

# 3. Test
python scripts/test_selectors.py
```

---

## Webhooks

### Sending Data

Data is sent via **outbox pattern**:

1. Data is saved to `webhook_outbox` table
2. Background process (every 15s) sends data
3. On error — retries (exponential backoff)

### Updating Webhook URL

If you updated `WEBHOOK_URL` in `.env`:

```bash
# Clear old webhook queue
python scripts/clear_webhook_queue.py
```

---

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

### Run Specific Tests

```bash
pytest tests/test_selectors.py -v
pytest tests/test_webhook_serializer.py -v
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures
├── test_selectors.py        # Selector tests
├── test_selector_utils.py   # Search utility tests
├── test_webhook_serializer.py # Serialization tests
├── test_latest_handler.py   # /latest handler tests
└── test_parser.py           # Parser tests
```

---

## Utilities

### `scripts/research_selectors.py`

Researches OLX.uz structure and finds stable selectors.

**Usage:**
```bash
python scripts/research_selectors.py
```

**Output:**
- `research_main_page.html` — main page
- `research_category_page.html` — category page
- `research_product_page.html` — product page

### `scripts/clear_webhook_queue.py`

Clears pending webhooks from the database.

**Usage:**
```bash
python scripts/clear_webhook_queue.py
```

---

## Project Structure

### Database

#### `products` Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Record ID |
| title | String | Listing title |
| price | Float | Price |
| currency | String | Currency (UZS/USD) |
| location | String | Location |
| precise_location | String | Precise location |
| url | String | Listing URL (unique) |
| category | String | Category |
| created_at | DateTime | Creation date |

#### `webhook_outbox` Table

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Event ID |
| target_url | String | Webhook URL |
| payload | JSON | Data to send |
| status | Enum | PENDING/SENT/DEAD |
| attempts | Integer | Attempt count |
| next_retry_at | DateTime | Next retry time |
| created_at | DateTime | Creation date |

#### `users` Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Record ID |
| tg_id | BigInteger | Telegram ID (supports large IDs) |
| username | String(255) | Username |
| is_admin | Boolean | Admin flag |
| is_banned | Boolean | Ban flag |
| ban_reason | Text | Ban reason |
| created_at | DateTime | Registration date |

#### `settings` Table

| Field | Type | Description |
|-------|------|-------------|
| key | String(255) | Setting key (PK) |
| value | Text | Setting value |

---

## Migrations

### Create New Migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current version
alembic current

# Migration history
alembic history
```

### Important Migrations

- `41025f4c2198` — Register existing tables in Alembic
- `0d757a1f5c48` — Update User model for BigInteger tg_id

### Main Modules

#### `config.py`

Centralized configuration with validation via pydantic-settings:
- Automatic loading from `.env`
- Validation of required fields on startup
- Type-safe access to settings

#### `db_handler/main.py`

Parsing functions:
- `parse_products_from_category()` — parse product list
- `parse_product_details()` — parse product details
- `extract_products_links()` — extract links
- `get_current_usd_rate()` — USD exchange rate

#### `db_handler/services/repository.py`

CRUD operations via SQLAlchemy:
- `list_latest_products()` — latest listings
- `list_products_for_export()` — data for export
- `upsert_user()` — create/update user
- `get_user_by_tg_id()` — search by Telegram ID
- `mark_admin_by_username()` — assign admin
- `set_ban_with_reason()` — ban user

#### `db_handler/http_client.py`

Lifecycle manager for HTTP client:
- `get_http_client()` — get global client
- `close_http_client()` — close client on shutdown

#### `parser/selectors.py`

Selector configuration:
- `CATEGORY_PAGE_SELECTORS` — for category page
- `PRODUCT_PAGE_SELECTORS` — for product page

#### `parser/selector_utils.py`

Utilities:
- `find_with_fallback()` — search with fallback
- `get_text_fallback()` — text extraction
- `validate_selectors()` — selector validation

#### `db_handler/services/outbox_service.py`

- `enqueue_webhook()` — add webhook to queue

#### `db_handler/services/outbox_processor.py`

- `process_outbox()` — process queue (every 15s)
- `deliver_event()` — deliver single event

#### `handlers/start.py`

Command handlers:
- `latest_command_handler()` — `/latest`
- `parse_command_handler()` — `/parse`
- `report_command_handler()` — `/report`
- All admin commands

#### `middlewares/db_session.py`

Middleware for automatic SQLAlchemy session injection into handlers.

#### `filters/is_admin.py`

Admin rights filter (creates its own session since filters execute before middleware).

---

## License

MIT License

Copyright (c) 2026 Xsenos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
---
