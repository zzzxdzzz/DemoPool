from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from ..db import get_session, init_db
from ..models import SessionEvent, User
from ..schemas import SessionCreate, SessionPublic
from ..deps import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionPublic)
def create_session(payload: SessionCreate, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    init_db()
    s = SessionEvent(**payload.dict(), host_id=current.id)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s

@router.get("", response_model=List[SessionPublic])
def list_sessions(location_id: int, session: Session = Depends(get_session)):
    items = session.exec(select(SessionEvent).where(SessionEvent.location_id == location_id).order_by(SessionEvent.starts_at.asc())).all()
    return items
