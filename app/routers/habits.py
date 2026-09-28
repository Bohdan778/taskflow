from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Habit, HabitLog, User
from app.schemas.habit import HabitCreate, HabitLogRead, HabitRead, HabitWithLogs
from app.security import get_current_user

router = APIRouter(prefix="/habits", tags=["habits"])


async def get_user_habit(
    habit_id: int, session: AsyncSession, current_user: User
) -> Habit:
    habit = await session.get(Habit, habit_id)
    if habit is None or habit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.post("", response_model=HabitRead, status_code=201)
async def create_habit(
    data: HabitCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    habit = Habit(
        name=data.name, description=data.description, user_id=current_user.id
    )
    session.add(habit)
    await session.commit()
    await session.refresh(habit)
    return habit


@router.get("", response_model=list[HabitWithLogs])
async def get_habits(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Habit)
        .where(Habit.user_id == current_user.id)
        .options(selectinload(Habit.logs))
        .order_by(Habit.id)
    )
    return result.scalars().all()


@router.post("/{habit_id}/logs", response_model=HabitLogRead, status_code=201)
async def log_habit(
    habit_id: int,
    log_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    habit = await get_user_habit(habit_id, session, current_user)
    day = log_date or date.today()
    if day > date.today():
        raise HTTPException(status_code=400, detail="Cannot log a future date")

    log = HabitLog(habit_id=habit.id, log_date=day)
    session.add(log)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Already logged for this date")
    await session.refresh(log)
    return log


@router.delete("/{habit_id}", status_code=204)
async def delete_habit(
    habit_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    habit = await get_user_habit(habit_id, session, current_user)
    await session.delete(habit)
    await session.commit()