from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_db
from app.auth.schemas import RegisterIn, LoginIn, TokenOut
from app.auth.service import register, login

router = APIRouter()

@router.post("/register", response_model=TokenOut)
async def register_api(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    token = await register(db, payload.email, payload.username, payload.password)
    return TokenOut(access_token=token)

@router.post("/login", response_model=TokenOut)
async def login_api(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    token = await login(db, payload.email, payload.password)
    return TokenOut(access_token=token)
