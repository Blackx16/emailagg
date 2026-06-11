import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# If running inside Celery workers or Beat, use NullPool to avoid event loop sharing issues.
is_celery = any("celery" in arg for arg in sys.argv)

engine_kwargs = {
    "echo": settings.APP_ENV == "development",
}

if is_celery:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
