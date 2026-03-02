from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .engine import Base
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, JSON, Enum, Float, func, Text, Column
)
from sqlalchemy.dialects.postgresql import UUID


class Product(Base):
    __tablename__ = "products"

    # Идентификатор записи
    id: Mapped[int] = mapped_column(primary_key=True)
    # Заголовок/описание — используем Text для произвольной длины
    title: Mapped[str] = mapped_column(Text)
    # Категория объявления
    category: Mapped[str] = mapped_column(String(100))
    # Дата и время создания (автоматически при создании записи)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Значение цены — может быть None если цена не указана
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Валюта — короткая строка (например, 'USD', 'UZS')
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    # Локация — хранится как строка
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    # Точное местоположение — более детальная информация
    precise_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # "parameters" — оригинальные данные от парсера, храним в JSONB
    parameters: Mapped[dict] = mapped_column(JSONB)
    # Идентификатор на OLX — может быть None, если не указано
    olx_id: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    # Ссылка — уникальное поле
    url: Mapped[str] = mapped_column(String(500), unique=True)


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DEAD = "DEAD"


class WebhookOutbox(Base):
    __tablename__ = "webhook_outbox"

    # Используем Mapped для типизации
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus), default=OutboxStatus.PENDING)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    next_retry_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
