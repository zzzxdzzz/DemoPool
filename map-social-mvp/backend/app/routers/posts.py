from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlmodel import Session, select
from ..db import get_session, init_db
from ..models import Post, User
from ..schemas import PostCreate, PostPublic
from ..deps import get_current_user

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("", response_model=PostPublic)
def create_post(payload: PostCreate, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    init_db()
    post = Post(**payload.dict(), author_id=current.id)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post

@router.get("", response_model=List[PostPublic])
def list_posts(location_id: int, session: Session = Depends(get_session)):
    posts = session.exec(select(Post).where(Post.location_id == location_id).order_by(Post.created_at.desc())).all()
    return posts
