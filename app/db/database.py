from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


#  Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
)


#  Async session factory 
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base model
class Base(DeclarativeBase):
    pass


#  Dependency
async def get_db():
    async with SessionLocal() as db:
        yield db
