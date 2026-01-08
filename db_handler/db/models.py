from _pydatetime import datetime

from sqlalchemy import String, Float, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from engine import Base

class RealEstate(Base):
    __tablename__ = "real_estates"

    # Идентификатор записи
    id: Mapped[int] = mapped_column(primary_key=True)
    # Заголовок/описание — используем Text для произвольной длины
    title: Mapped[str] = mapped_column(Text)
    # Дата и время создания (автоматически при создании записи)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Значение цены — может быть None если цена не указана
    price_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Валюта — короткая строка (например, 'USD', 'UZS')
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    # Локация — хранится как строка
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    # Точное местоположение — более детальная информация
    precise_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # "parameters" — оригинальные данные от парсера, храним в JSONB
    parameters: Mapped[dict] = mapped_column(JSONB)
    # ID на OLX — может быть None если не указано
    olx_id: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    # URL — уникальное поле
    url: Mapped[str] = mapped_column(String(500), unique=True)
