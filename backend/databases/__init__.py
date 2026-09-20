from databases.engine_start import engine, SessionLocal, get_db
from databases.users_db import Base, User
from databases.businesses_db import Business


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
