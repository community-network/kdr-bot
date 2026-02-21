from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from utils.meta_singleton import MetaSingleton
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class DatabaseSingleton(metaclass=MetaSingleton):
    def __init__(self, db_url):
        self.dburl = db_url
        self.engine = None
        self.base = Base
        self.session = None

    async def init_db(self):
        self.engine = create_async_engine(self.dburl, echo=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.create_all)

    async def close_async(self):
        # Use on shutdown
        if self.engine is not None:
            await self.engine.dispose()

    def create_session(self) -> AsyncSession:
        session_maker = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        return session_maker()
