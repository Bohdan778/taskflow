from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import User
from schemas import Token, UserCreate, UserLogin, UserRead
from security import create_access_token, ph

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=data.email, password_hash=ph.hash(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    invalid = HTTPException(status_code=401, detail="Invalid email or password")
    if user is None:
        raise invalid
    try:
        ph.verify(user.password_hash, data.password)
    except VerifyMismatchError:
        raise invalid

    return Token(access_token=create_access_token(user.id))