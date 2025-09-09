from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException
from app.social.models import Follow
from app.posts.models import Post

async def follow(db: AsyncSession, follower_id: int, followee_id: int):
    if follower_id == followee_id:
        raise HTTPException(400, "cannot follow yourself")
    f = Follow(follower_id=follower_id, followee_id=followee_id)
    db.add(f)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
    return {"ok": True}

async def unfollow(db: AsyncSession, follower_id: int, followee_id: int):
    res = await db.execute(select(Follow).where(Follow.follower_id==follower_id, Follow.followee_id==followee_id))
    rel = res.scalar_one_or_none()
    if rel:
        await db.delete(rel)
        await db.commit()
    return {"ok": True}

async def feed(db: AsyncSession, user_id: int, offset=0, limit=20):
    # 查询关注的人
    res = await db.execute(select(Follow.followee_id).where(Follow.follower_id == user_id))
    ids = [row[0] for row in res.all()]
    if not ids:
        return []
    q = select(Post).where(Post.author_id.in_(ids)).order_by(desc(Post.id)).offset(offset).limit(limit)
    res2 = await db.execute(q)
    return res2.scalars().all()
