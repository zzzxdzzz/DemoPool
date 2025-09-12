from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlmodel import Session, select
from ..db import get_session, init_db
from ..models import Location, User
from ..schemas import LocationCreate, LocationPublic
from ..deps import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])

@router.post("", response_model=LocationPublic)
def create_location(payload: LocationCreate, current: User = Depends(get_current_user), session: Session = Depends(get_session)):
    init_db()
    loc = Location(**payload.dict(), created_by_id=current.id)
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc

@router.get("", response_model=List[LocationPublic])
def list_locations(
    session: Session = Depends(get_session),
    # Optional bbox search: minLon,minLat,maxLon,maxLat
    bbox: Optional[str] = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    kind: Optional[str] = None,
):
    q = select(Location)
    if kind:
        q = q.where(Location.kind == kind)
    locs = session.exec(q).all()
    if bbox:
        try:
            minLon, minLat, maxLon, maxLat = [float(x) for x in bbox.split(",")]
            locs = [l for l in locs if (minLon <= l.lon <= maxLon and minLat <= l.lat <= maxLat)]
        except Exception:
            pass
    return locs
