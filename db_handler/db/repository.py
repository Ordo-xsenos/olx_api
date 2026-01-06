from sqlalchemy import select
from engine import get_sessionmaker
from models import RealEstate

class RealEstateRepository:

    async def save(self, estate: RealEstate) -> None:
        # Получаем sessionmaker лениво и открываем сессию
        session_local = get_sessionmaker()
        async with session_local() as session:
            try:
                session.add(estate)
                await session.commit()
            except Exception:
                # при ошибке откатываем транзакцию и пробрасываем дальше
                await session.rollback()
                raise

    async def get_existing_urls(self) -> set[str]:
        session_local() = get_sessionmaker()
        async with session_local() as session:
            result = await session.execute(select(RealEstate.url))
            # scalars() возвращает ScalarResult — преобразуем в множество строк
            urls = result.scalars().all()
            return set(urls)
