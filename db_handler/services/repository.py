from typing import List, Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from db_handler.db.models import Product, User, Settings


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    uname = username.strip()
    if uname.startswith("@"):
        uname = uname[1:]
    return uname.lower()


async def list_latest_products(
    session: AsyncSession,
    limit: int = 10,
    category: Optional[str] = None,
) -> List[dict]:
    stmt = select(Product).order_by(Product.created_at.desc())

    if category and category != "all":
        normalized = category.strip("/ ")
        stmt = stmt.where(Product.category == normalized)

    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price,
            "currency": p.currency,
            "location": p.location,
            "precise_location": p.precise_location,
            "url": p.url,
            "category": p.category,
            "created_at": p.created_at,
        }
        for p in products
    ]


async def list_products_for_export(
    session: AsyncSession,
    category: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[dict]:
    stmt = select(Product).order_by(Product.created_at.desc())

    if category and category != "all":
        normalized = category.strip("/ ")
        stmt = stmt.where(Product.category == normalized)

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price,
            "currency": p.currency,
            "location": p.location,
            "precise_location": p.precise_location,
            "url": p.url,
            "category": p.category,
            "created_at": p.created_at,
        }
        for p in products
    ]


async def delete_missing_by_category(
    session: AsyncSession, category: str, urls: List[str]
) -> int:
    if not urls:
        return 0

    normalized = category.strip("/ ")
    stmt = delete(Product).where(
        Product.category == normalized,
        Product.url.notin_(urls)
    )

    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount


async def upsert_user(
    session: AsyncSession, tg_id: int, username: str | None
) -> dict | None:
    username_norm = _normalize_username(username)

    # Ищем пользователя по tg_id
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    existing_by_id = result.scalar_one_or_none()

    if existing_by_id:
        current_username_norm = _normalize_username(existing_by_id.username)
        if username_norm and current_username_norm != username_norm:
            # Проверяем не занят ли username
            stmt = select(User).where(func.lower(User.username) == username_norm.lower())
            result = await session.execute(stmt)
            owner = result.scalar_one_or_none()

            if not owner or owner.tg_id == tg_id:
                existing_by_id.username = username_norm
                await session.commit()

        return {
            "tg_id": existing_by_id.tg_id,
            "username": existing_by_id.username,
            "is_admin": existing_by_id.is_admin,
            "is_banned": existing_by_id.is_banned,
            "ban_reason": existing_by_id.ban_reason,
            "created_at": existing_by_id.created_at,
        }

    if username_norm:
        # Ищем по username
        stmt = select(User).where(func.lower(User.username) == username_norm.lower())
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.tg_id != tg_id:
            # Если username существует без tg_id, обновляем
            if existing.tg_id is None:
                existing.tg_id = tg_id
                await session.commit()
                return {
                    "tg_id": existing.tg_id,
                    "username": existing.username,
                    "is_admin": existing.is_admin,
                    "is_banned": existing.is_banned,
                    "ban_reason": existing.ban_reason,
                    "created_at": existing.created_at,
                }
            return {
                "tg_id": existing.tg_id,
                "username": existing.username,
                "is_admin": existing.is_admin,
                "is_banned": existing.is_banned,
                "ban_reason": existing.ban_reason,
                "created_at": existing.created_at,
            }

    # Создаем нового пользователя
    new_user = User(tg_id=tg_id, username=username_norm)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return {
        "tg_id": new_user.tg_id,
        "username": new_user.username,
        "is_admin": new_user.is_admin,
        "is_banned": new_user.is_banned,
        "ban_reason": new_user.ban_reason,
        "created_at": new_user.created_at,
    }


async def promote_admin_if_username(
    session: AsyncSession, tg_id: int, username: str | None
) -> bool:
    if not username:
        return False

    # Проверяем существует ли админ с таким username
    stmt = select(User).where(
        func.lower(User.username) == username.lower(),
        User.is_admin == True
    )
    result = await session.execute(stmt)
    admin_exists = result.scalar_one_or_none()

    if not admin_exists:
        return False

    # Обновляем пользователя
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.is_admin = True
        await session.commit()
        return True

    return False


async def mark_admin_by_username(session: AsyncSession, username: str) -> int:
    username_norm = _normalize_username(username)

    # Ищем пользователя
    stmt = select(User).where(func.lower(User.username) == username_norm.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.is_admin = True
        await session.commit()
        return 1
    else:
        # Создаем нового админа
        new_user = User(username=username_norm, is_admin=True)
        session.add(new_user)
        await session.commit()
        return 1


async def mark_admin_by_tg_id(session: AsyncSession, tg_id: int) -> int:
    # Ищем пользователя
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.is_admin = True
        await session.commit()
        return 1
    else:
        # Создаем нового админа
        new_user = User(tg_id=tg_id, is_admin=True)
        session.add(new_user)
        await session.commit()
        return 1


async def set_ban_by_username(session: AsyncSession, username: str, banned: bool) -> int:
    username_norm = _normalize_username(username)

    # Ищем пользователя
    stmt = select(User).where(func.lower(User.username) == username_norm.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.is_banned = banned
        user.ban_reason = "manual" if banned else None
        await session.commit()
        return 1
    else:
        # Создаем нового пользователя с баном
        new_user = User(username=username_norm, is_banned=banned, ban_reason="manual" if banned else None)
        session.add(new_user)
        await session.commit()
        return 1


async def set_ban_with_reason(
    session: AsyncSession, username: str, banned: bool, reason: str | None
) -> int:
    username_norm = _normalize_username(username)

    # Ищем пользователя
    stmt = select(User).where(func.lower(User.username) == username_norm.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.is_banned = banned
        user.ban_reason = reason
        await session.commit()
        return 1
    else:
        # Создаем нового пользователя с баном
        new_user = User(username=username_norm, is_banned=banned, ban_reason=reason)
        session.add(new_user)
        await session.commit()
        return 1


async def set_allow_non_admins(session: AsyncSession, allowed: bool) -> None:
    # Ищем настройку
    stmt = select(Settings).where(Settings.key == "allow_non_admins")
    result = await session.execute(stmt)
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = "1" if allowed else "0"
    else:
        new_setting = Settings(key="allow_non_admins", value="1" if allowed else "0")
        session.add(new_setting)

    await session.commit()


async def get_allow_non_admins(session: AsyncSession) -> bool:
    stmt = select(Settings).where(Settings.key == "allow_non_admins")
    result = await session.execute(stmt)
    setting = result.scalar_one_or_none()

    if not setting:
        return True

    return setting.value == "1"


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> dict | None:
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return {
        "tg_id": user.tg_id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_banned": user.is_banned,
        "ban_reason": user.ban_reason,
        "created_at": user.created_at,
    }


async def get_user_by_username(session: AsyncSession, username: str) -> dict | None:
    username_norm = _normalize_username(username)
    if not username_norm:
        return None

    stmt = select(User).where(func.lower(User.username) == username_norm.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return {
        "tg_id": user.tg_id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_banned": user.is_banned,
        "ban_reason": user.ban_reason,
        "created_at": user.created_at,
    }


async def list_users(session: AsyncSession, limit: int = 200) -> List[dict]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "tg_id": u.tg_id,
            "username": u.username,
            "is_admin": u.is_admin,
            "is_banned": u.is_banned,
            "ban_reason": u.ban_reason,
            "created_at": u.created_at,
        }
        for u in users
    ]


async def get_stats(session: AsyncSession) -> dict:
    # Подсчитываем статистику
    products_count = await session.scalar(select(func.count()).select_from(Product))
    users_count = await session.scalar(select(func.count()).select_from(User))
    admins_count = await session.scalar(
        select(func.count()).select_from(User).where(User.is_admin == True)
    )
    banned_count = await session.scalar(
        select(func.count()).select_from(User).where(User.is_banned == True)
    )

    return {
        "products": products_count or 0,
        "users": users_count or 0,
        "admins": admins_count or 0,
        "banned": banned_count or 0,
    }


async def delete_user_by_username(session: AsyncSession, username: str) -> int:
    username_norm = _normalize_username(username)
    if not username_norm:
        return 0

    if username_norm == "no_username":
        # Удаляем пользователей без username
        stmt = delete(User).where(User.username.is_(None))
    else:
        stmt = delete(User).where(func.lower(User.username) == username_norm.lower())

    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount


async def delete_user_by_tg_id(session: AsyncSession, tg_id: int) -> int:
    stmt = delete(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount
