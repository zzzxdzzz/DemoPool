from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.users.models import User
from app.common.security import hash_password, verify_password, create_access_token

async def register(db: AsyncSession, email: str, username: str, password: str) -> str:
    exists = await db.execute(select(User).where((User.email == email) | (User.username == username)))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already exists")
    user = User(email=email, username=username, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return create_access_token(user.id)

async def login(db: AsyncSession, email: str, password: str) -> str:
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return create_access_token(user.id)
