from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import User

async def get_user(db: AsyncSession, user_id: int):
    return await db.get(User, user_id)

async def update_bio(db: AsyncSession, user_id: int, bio: str | None):
    user = await db.get(User, user_id)
    if not user:
        return None
    user.bio = bio
    await db.commit()
    await db.refresh(user)
    return user
