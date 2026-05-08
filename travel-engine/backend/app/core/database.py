from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from typing import AsyncGenerator

from app.core.config import settings


def _async_engine_kwargs():
    url = settings.DATABASE_URL
    kw: dict = {"echo": settings.SQLALCHEMY_ECHO, "pool_pre_ping": True}
    if url.startswith("postgresql") or url.startswith("postgres"):
        kw["pool_timeout"] = 60
        # Fail fast-ish on bad Cloud SQL / network instead of hanging past probe timeout.
        kw["connect_args"] = {"timeout": 30}
    return kw


engine = create_async_engine(settings.DATABASE_URL, **_async_engine_kwargs())

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
