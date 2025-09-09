from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    # 仅用于演示：自动建表（生产用 Alembic 迁移）
    from app.users.models import User
    from app.posts.models import Post, Comment, Like
    from app.social.models import Follow
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
