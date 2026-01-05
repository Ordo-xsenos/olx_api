from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from engine import Base

class RealEstate(Base):
    __tablename__ = "real_estates"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    price_value: Mapped[float | None]
    currency: Mapped[str]
    location: Mapped[str]
    raw: Mapped[dict] = mapped_column(JSONB)
    url: Mapped[str] = mapped_column(unique=True)
