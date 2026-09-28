from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Task, User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.security import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_user_task(
    task_id: int, session: AsyncSession, current_user: User
) -> Task:
    task = await session.get(Task, task_id)
    if task is None or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskRead)
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


@router.get("", response_model=list[TaskRead])
async def get_tasks(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Task).where(Task.user_id == current_user.id).order_by(Task.id)
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_user_task(task_id, session, current_user)


@router.patch("/{task_id}", response_model=TaskRead)
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


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = await get_user_task(task_id, session, current_user)
    await session.delete(task)
    await session.commit()