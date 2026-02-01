from typing import List, Optional

from db_handler.db_class import PostgresHandler


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    uname = username.strip()
    if uname.startswith("@"):
        uname = uname[1:]
    return uname.lower()


async def list_latest_products(
    db: PostgresHandler,
    limit: int = 10,
    category: Optional[str] = None,
) -> List[dict]:
    query = """
        SELECT id, title, price, currency, location, precise_location, url, category, created_at
        FROM products
    """
    params = []
    if category and category != "all":
        normalized = category.strip("/ ")
        query += " WHERE category = $1"
        params.append(normalized)
    query += " ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    return await db.fetch_query(query, *params)


async def list_products_for_export(
    db: PostgresHandler,
    category: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[dict]:
    query = """
        SELECT id, title, price, currency, location, precise_location, url, category, created_at
        FROM products
    """
    params = []
    if category and category != "all":
        normalized = category.strip("/ ")
        query += " WHERE category = $1"
        params.append(normalized)
    query += " ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    return await db.fetch_query(query, *params)


async def delete_missing_by_category(
    db: PostgresHandler, category: str, urls: List[str]
) -> int:
    if not urls:
        return 0
    normalized = category.strip("/ ")
    query = """
        DELETE FROM products
        WHERE category = $1
          AND NOT (url = ANY($2::text[]))
    """
    result = await db.execute_query(query, normalized, urls)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def upsert_user(
    db: PostgresHandler, tg_id: int, username: str | None
) -> dict | None:
    username_norm = _normalize_username(username)
    existing_by_id = await get_user_by_tg_id(db, tg_id)
    if existing_by_id:
        current_username_norm = _normalize_username(existing_by_id.get("username"))
        if username_norm and current_username_norm != username_norm:
            owner = await get_user_by_username(db, username_norm)
            if not owner or owner.get("tg_id") == tg_id:
                await db.execute_query(
                    "UPDATE users SET username = $2 WHERE tg_id = $1",
                    tg_id,
                    username_norm,
                )
                existing_by_id["username"] = username_norm
        return existing_by_id
    if username_norm:
        existing = await get_user_by_username(db, username_norm)
        if existing and existing.get("tg_id") != tg_id:
            update_by_username = """
                UPDATE users
                SET tg_id = $1
                WHERE lower(regexp_replace(username, '^@', '')) = lower($2)
                  AND tg_id IS NULL
                RETURNING *
            """
            updated = await db.fetchrow_query(
                update_by_username, tg_id, username_norm
            )
            if updated:
                return updated
            return existing

    query = """
        INSERT INTO users (tg_id, username)
        VALUES ($1, $2)
        ON CONFLICT (tg_id) DO UPDATE
        SET username = EXCLUDED.username
        RETURNING *
    """
    return await db.fetchrow_query(query, tg_id, username_norm)


async def promote_admin_if_username(
    db: PostgresHandler, tg_id: int, username: str | None
) -> bool:
    if not username:
        return False
    query = """
        UPDATE users u
        SET is_admin = TRUE
        WHERE u.tg_id = $1
          AND EXISTS (SELECT 1 FROM users WHERE username = $2 AND is_admin = TRUE)
    """
    result = await db.execute_query(query, tg_id, username)
    if not result:
        return False
    try:
        return int(result.split()[-1]) > 0
    except Exception:
        return False


async def mark_admin_by_username(db: PostgresHandler, username: str) -> int:
    username_norm = _normalize_username(username)
    query = """
        INSERT INTO users (username, is_admin)
        VALUES ($1, TRUE)
        ON CONFLICT (username) DO UPDATE
        SET is_admin = TRUE
    """
    result = await db.execute_query(query, username_norm)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def mark_admin_by_tg_id(db: PostgresHandler, tg_id: int) -> int:
    query = """
        INSERT INTO users (tg_id, is_admin)
        VALUES ($1, TRUE)
        ON CONFLICT (tg_id) DO UPDATE
        SET is_admin = TRUE
    """
    result = await db.execute_query(query, tg_id)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def set_ban_by_username(db: PostgresHandler, username: str, banned: bool) -> int:
    username_norm = _normalize_username(username)
    query = """
        INSERT INTO users (username, is_banned, ban_reason)
        VALUES ($1, $2, $3)
        ON CONFLICT (username) DO UPDATE
        SET is_banned = EXCLUDED.is_banned,
            ban_reason = EXCLUDED.ban_reason
    """
    result = await db.execute_query(
        query,
        username_norm,
        banned,
        None if not banned else "manual",
    )
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def set_ban_with_reason(
    db: PostgresHandler, username: str, banned: bool, reason: str | None
) -> int:
    username_norm = _normalize_username(username)
    query = """
        INSERT INTO users (username, is_banned, ban_reason)
        VALUES ($1, $2, $3)
        ON CONFLICT (username) DO UPDATE
        SET is_banned = EXCLUDED.is_banned,
            ban_reason = EXCLUDED.ban_reason
    """
    result = await db.execute_query(query, username_norm, banned, reason)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def set_allow_non_admins(db: PostgresHandler, allowed: bool) -> None:
    query = """
        INSERT INTO settings (key, value)
        VALUES ('allow_non_admins', $1)
        ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value
    """
    await db.execute_query(query, "1" if allowed else "0")


async def get_allow_non_admins(db: PostgresHandler) -> bool:
    query = "SELECT value FROM settings WHERE key = 'allow_non_admins'"
    row = await db.fetchrow_query(query)
    if not row:
        return True
    return row.get("value") == "1"


async def get_user_by_tg_id(db: PostgresHandler, tg_id: int) -> dict | None:
    query = "SELECT * FROM users WHERE tg_id = $1"
    return await db.fetchrow_query(query, tg_id)


async def get_user_by_username(db: PostgresHandler, username: str) -> dict | None:
    username_norm = _normalize_username(username)
    if not username_norm:
        return None
    query = """
        SELECT * FROM users
        WHERE lower(regexp_replace(username, '^@', '')) = lower($1)
    """
    return await db.fetchrow_query(query, username_norm)


async def list_users(db: PostgresHandler, limit: int = 200) -> List[dict]:
    query = """
        SELECT tg_id, username, is_admin, is_banned, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT $1
    """
    return await db.fetch_query(query, limit)


async def get_stats(db: PostgresHandler) -> dict:
    query = """
        SELECT
            (SELECT COUNT(*) FROM products) AS products,
            (SELECT COUNT(*) FROM users) AS users,
            (SELECT COUNT(*) FROM users WHERE is_admin = TRUE) AS admins,
            (SELECT COUNT(*) FROM users WHERE is_banned = TRUE) AS banned
    """
    row = await db.fetchrow_query(query)
    return row or {"products": 0, "users": 0, "admins": 0, "banned": 0}


async def delete_user_by_username(db: PostgresHandler, username: str) -> int:
    username_norm = _normalize_username(username)
    if not username_norm:
        return 0
    if username_norm == "no_username":
        query = "DELETE FROM users WHERE username IS NULL"
        result = await db.execute_query(query)
        if not result:
            return 0
        try:
            return int(result.split()[-1])
        except Exception:
            return 0
    query = """
        DELETE FROM users
        WHERE lower(regexp_replace(username, '^@', '')) = lower($1)
    """
    result = await db.execute_query(query, username_norm)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def delete_user_by_tg_id(db: PostgresHandler, tg_id: int) -> int:
    query = "DELETE FROM users WHERE tg_id = $1"
    result = await db.execute_query(query, tg_id)
    if not result:
        return 0
    try:
        return int(result.split()[-1])
    except Exception:
        return 0
