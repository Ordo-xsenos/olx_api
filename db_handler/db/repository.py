from sqlalchemy import select
from engine import SessionLocal
from models import RealEstate

class RealEstateRepository:

    async def save(self, estate: RealEstate):
        async with SessionLocal() as session:
            session.add(estate)
            await session.commit()

    async def get_existing_urls(self) -> set[str]:
        async with SessionLocal() as session:
            rows = await session.execute(select(RealEstate.url))
            return {r[0] for r in rows}
