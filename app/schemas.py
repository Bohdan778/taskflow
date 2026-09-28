from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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