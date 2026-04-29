# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot that scrapes product listings from OLX.uz (Uzbekistan's classifieds site), stores them in PostgreSQL, and delivers data via webhooks using the outbox pattern. Built with aiogram 3.x, SQLAlchemy 2.x, and APScheduler.

## Development Commands

### Running the bot
```bash
python aiogram_run.py
```

### Running the parser standalone
```bash
python db_handler/main.py
```

### Database migrations
```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_selectors.py -v

# Run by marker
pytest -m unit
pytest -m "not slow"
```

### Linting
```bash
# Auto-fix with ruff
ruff check --fix .

# Type checking
mypy .
```

## Architecture

### Core Flow
1. **Scraping**: `parser/main_parser.py` orchestrates category scraping → `db_handler/main.py` handles HTML parsing with fallback selectors
2. **Persistence**: `db_handler/services/persistense.py` saves normalized data to PostgreSQL via SQLAlchemy ORM
3. **Webhook delivery**: `db_handler/services/outbox_service.py` enqueues events → `db_handler/services/outbox_processor.py` delivers them (runs every 15s via APScheduler)
4. **Bot handlers**: `handlers/start.py` processes Telegram commands with FSM for parsing configuration

### Database Layer
- **SQLAlchemy 2.x ORM** for all database operations
- **AsyncSession** injected via `DbSessionMiddleware` 
- **Bulk operations** via `insert().on_conflict_do_update()` for performance
- **Alembic** for schema migrations

### Selector System (Critical)
The parser uses **fallback selectors** to handle OLX.uz HTML changes. Priority order:
1. `data-testid` attributes (most stable)
2. CSS classes (can change)
3. Semantic tags (last resort)

Selectors are defined in `parser/selectors.py` as lists. The `find_with_fallback()` function in `parser/selector_utils.py` tries each selector until one matches.

**When OLX.uz changes their HTML:**
1. Run `python scripts/research_selectors.py` to capture current HTML structure
2. Update `parser/selectors.py` with new selectors (add to existing lists, don't replace)
3. Test with `pytest tests/test_selectors.py`

### Database Models
- `Product`: Stores scraped listings. `url` field is unique and normalized (no query params). `price` stores original value, `currency` indicates USD/UZS. `parameters` is JSONB for flexible attributes.
- `WebhookOutbox`: Outbox pattern for reliable webhook delivery. Status: PENDING → SENT/FAILED/DEAD. Exponential backoff on retry.
- `User`: Telegram users with admin/ban flags. `tg_id` is BigInteger to support large Telegram IDs.
- `Settings`: Key-value store for bot configuration.

### Async Patterns
- Uses `httpx.AsyncClient` with semaphore (MAX_CONCURRENT_REQUESTS=5) to avoid rate limiting
- HTTP client managed via lifecycle manager in `db_handler/http_client.py`
- All DB operations are async via SQLAlchemy async engine
- Parser uses `asyncio.gather()` for parallel product detail fetching

### Price Handling
Prices are parsed from text and stored with currency. The `parse_price_value()` function extracts numeric value and detects USD vs UZS. USD prices are converted to UZS using live exchange rate from exchangerate-api.com (cached per parsing session). "Договор" (negotiable) prices return `None` value with `NEGOTIABLE` currency.

### Scheduling
APScheduler (AsyncIOScheduler) runs:
- Outbox processor: every 15 seconds (`db_handler/scheduler/outbox_scheduler.py`)
- Category parsing: cron schedule from `PARSE_SCHEDULE_TIME` env var
- Hourly category sweep: `work_time/time_func.py:parse_all_categories_once()`

Timezone: Asia/Tashkent

## Configuration

Configuration is managed via `config.py` using pydantic-settings for validation.

Environment variables (`.env` file):
- `DATABASE_URL`: PostgreSQL connection (asyncpg format) - **required**
- `TOKEN`: Bot token - **required**
- `ADMINS`: Comma-separated list of @usernames or tg_ids
- `WEBHOOK_URL`: Target for webhook delivery (optional)
- `SCHEDULE_CATEGORY_ID`: Category path for scheduled parsing (e.g., `/nedvizhimost/`)
- `PARSE_SCHEDULE_TIME`: Cron time in HH:MM format
- `TELEGRAM_CHAT_ID`: Chat for scheduled parsing notifications
- `CLEANUP_MISSING`: Set to "1" to delete products not found in latest scrape (only if >90% success rate)
- `MAX_CONCURRENT_REQUESTS`: Concurrent HTTP requests limit (default: 5)
- `BATCH_SIZE`: Bulk insert batch size (default: 200)
- `WEBHOOK_TIMEOUT_SECONDS`: Webhook timeout (default: 10.0)

All required fields are validated on startup. Missing required fields will prevent bot from starting with clear error message.

## Bot Commands

User commands: `/start`, `/parse`, `/report`, `/latest [N]`, `/filters`

Admin commands: `/add_admin`, `/ban`, `/unban`, `/stats`, `/users`, `/del_user`, `/del_user_id`, `/allow_all`, `/deny_all`, `/whoami`

Admin filter is in `filters/is_admin.py`. It creates its own session since filters execute before middleware. Access control logic is in `handlers/start.py:_ensure_user()`.

## Testing Notes

- `conftest.py` provides fixtures for mock HTML and database sessions
- Tests use `asyncio_mode = auto` (pytest-asyncio)
- Selector tests validate that fallback chains work on real HTML snapshots
- Webhook serializer tests ensure proper JSON structure for external systems

## Common Pitfalls

1. **Don't use `git add -A`** when committing - stage specific files to avoid committing `.env` or other sensitive files
2. **Selector updates**: Always add new selectors to the list, don't replace existing ones (fallback chain)
3. **URL normalization**: Use `normalize_listing_url()` before saving to DB to avoid duplicates from query params
4. **HTTP client lifecycle**: HTTP client is managed via `db_handler/http_client.py` and closed properly on shutdown
5. **Price conversion**: Always pass `usd_rate` to `parse_product_details()` - fetch it once per scraping session, not per product
6. **Outbox delivery**: Webhook failures are retried with exponential backoff. Use `scripts/clear_webhook_queue.py` if you change `WEBHOOK_URL` to clear stale events
7. **BigInteger for tg_id**: User model uses BigInteger for `tg_id` to support large Telegram IDs (>2^31)

## Utility Scripts

- `scripts/research_selectors.py`: Captures HTML from OLX.uz for selector analysis
- `scripts/clear_webhook_queue.py`: Clears pending webhooks from outbox table

## Recent Changes

- Migrated from PostgresHandler to SQLAlchemy ORM for all database operations
- Added pydantic-settings for configuration validation
- Implemented HTTP client lifecycle management
- Fixed SQL injection vulnerabilities by using parameterized queries
- Improved error handling with specific exception types
- Changed `tg_id` from Integer to BigInteger to support large Telegram IDs
