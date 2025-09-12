from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from ..db import get_session, init_db
from ..models import Comment, User
from ..schemas import CommentCreate, CommentPublic
from ..deps import get_current_user

router = APIRouter(prefix="/comments", tags=["comments"])

@router.post("", response_model=CommentPublic)
def create_comment(payload: CommentCreate, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    init_db()
    c = Comment(**payload.dict(), author_id=current.id)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c

@router.get("", response_model=List[CommentPublic])
def list_comments(post_id: int, session: Session = Depends(get_session)):
    items = session.exec(select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc())).all()
    return items
