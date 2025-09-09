from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_db
from app.deps import current_user
from app.users.schemas import UserOut
from app.users.service import get_user, update_bio

router = APIRouter()

@router.get("/me", response_model=UserOut)
async def me(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    u = await get_user(db, user.id)
    return u

@router.patch("/me", response_model=UserOut)
async def update_me(bio: str | None = None, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    u = await update_bio(db, user.id, bio)
    return u
