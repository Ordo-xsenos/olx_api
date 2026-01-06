from sqlalchemy import String, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from engine import Base

class RealEstate(Base):
    __tablename__ = "real_estates"

    # Идентификатор записи
    id: Mapped[int] = mapped_column(primary_key=True)
    # Заголовок/описание — используем Text для произвольной длины
    title: Mapped[str] = mapped_column(Text)
    # Значение цены — может быть None если цена не указана
    price_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Валюта — короткая строка (например, 'USD', 'UZS')
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    # Локация — хранится как строка
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    # "raw" — оригинальные данные от парсера, храним в JSONB
    raw: Mapped[dict] = mapped_column(JSONB)
    # URL — уникальное поле
    url: Mapped[str] = mapped_column(String(500), unique=True)
