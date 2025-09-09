from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_db
from app.deps import current_user
from app.posts.schemas import PostIn, PostOut, CommentIn, CommentOut
from app.posts.service import create_post, list_user_posts, add_comment, like_post

router = APIRouter()

@router.post("/", response_model=PostOut)
async def create_post_api(payload: PostIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    post = await create_post(db, user.id, payload.content)
    return post

@router.get("/u/{user_id}")
async def list_user_posts_api(user_id: int, offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    posts = await list_user_posts(db, user_id, offset, limit)
    return posts

@router.post("/{post_id}/comments", response_model=CommentOut)
async def comment_api(post_id: int, payload: CommentIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await add_comment(db, user.id, post_id, payload.content)
    return c

@router.post("/{post_id}/like")
async def like_api(post_id: int, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await like_post(db, user.id, post_id)
