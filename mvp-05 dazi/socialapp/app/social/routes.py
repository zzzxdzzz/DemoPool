from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_db
from app.deps import current_user
from app.social.service import follow, unfollow, feed

router = APIRouter()

@router.post("/follow/{user_id}")
async def follow_api(user_id: int, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await follow(db, user.id, user_id)

@router.post("/unfollow/{user_id}")
async def unfollow_api(user_id: int, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await unfollow(db, user.id, user_id)

@router.get("/feed")
async def feed_api(offset: int = 0, limit: int = 20, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    items = await feed(db, user.id, offset, limit)
    return items
