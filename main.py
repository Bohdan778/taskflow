from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Task

app = FastAPI()


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date
    priority: int = Field(default=3, ge=1, le=5)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    due_date: date
    priority: int
    completed: bool
    created_at: datetime
    
class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    completed: bool | None = None


@app.get("/")
async def root():
    return {"message": "TaskFlow is alive"}


@app.post("/tasks", response_model=TaskRead)
async def create_task(task: TaskCreate, session: AsyncSession = Depends(get_session)):
    new_task = Task(
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task

@app.get("/tasks", response_model=list[TaskRead])
async def get_tasks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).order_by(Task.id))
    return result.scalars().all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int, data: TaskUpdate, session: AsyncSession = Depends(get_session)
):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    await session.commit()