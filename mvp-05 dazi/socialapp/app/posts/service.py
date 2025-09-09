from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException
from app.posts.models import Post, Comment, Like

async def create_post(db: AsyncSession, user_id: int, content: str) -> Post:
    post = Post(author_id=user_id, content=content)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post

async def list_user_posts(db: AsyncSession, user_id: int, offset=0, limit=20):
    res = await db.execute(select(Post).where(Post.author_id == user_id).order_by(desc(Post.id)).offset(offset).limit(limit))
    return res.scalars().all()

async def add_comment(db: AsyncSession, user_id: int, post_id: int, content: str) -> Comment:
    # 检查 post 存在
    if not await db.get(Post, post_id):
        raise HTTPException(404, "Post not found")
    c = Comment(post_id=post_id, author_id=user_id, content=content)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

async def like_post(db: AsyncSession, user_id: int, post_id: int):
    if not await db.get(Post, post_id):
        raise HTTPException(404, "Post not found")
    like = Like(post_id=post_id, user_id=user_id)
    db.add(like)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # 已点过赞
    return {"ok": True}
