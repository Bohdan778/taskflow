import os
from datetime import date, datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Task, User

app = FastAPI()
ph = PasswordHasher()
SECRET_KEY = os.environ["SECRET_KEY"]
bearer_scheme = HTTPBearer()


# ---------- Schemas ----------


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date
    priority: int = Field(default=3, ge=1, le=5)
    category: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    due_date: date
    priority: int
    completed: bool
    created_at: datetime
    category: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    completed: bool | None = None
    category: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Dependencies ----------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_user_task(
    task_id: int, session: AsyncSession, current_user: User
) -> Task:
    task = await session.get(Task, task_id)
    if task is None or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ---------- Root ----------


@app.get("/")
async def root():
    return {"message": "TaskFlow is alive"}


# ---------- Tasks ----------


@app.post("/tasks", response_model=TaskRead)
async def create_task(
    task: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    new_task = Task(
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
        category=task.category,
        user_id=current_user.id,
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=list[TaskRead])
async def get_tasks(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Task).where(Task.user_id == current_user.id).order_by(Task.id)
    )
    return result.scalars().all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_user_task(task_id, session, current_user)


@app.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = await get_user_task(task_id, session, current_user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = await get_user_task(task_id, session, current_user)
    await session.delete(task)
    await session.commit()

# ---------- Auth ----------


@app.post("/auth/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=data.email, password_hash=ph.hash(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
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

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = jwt.encode(
        {"sub": str(user.id), "exp": expire}, SECRET_KEY, algorithm="HS256"
    )
    return Token(access_token=token)