from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Habit, ScheduleEvent, Task, User
from app.schemas.stats import StatsOverview
from app.security import get_current_user
from app.services.habit_stats import calculate_streaks

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
async def get_overview(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Задачі: один запит, дві агрегатні колонки одразу
    task_row = (
        await session.execute(
            select(
                func.count(Task.id),
                func.sum(case((Task.completed.is_(True), 1), else_=0)),
            ).where(Task.user_id == current_user.id)
        )
    ).one()
    tasks_total = task_row[0]
    tasks_completed = task_row[1] or 0
    tasks_pending = tasks_total - tasks_completed

    # Звички: скільки всього + найкраща активна серія
    habits_result = await session.execute(
        select(Habit)
        .where(Habit.user_id == current_user.id)
        .options(selectinload(Habit.logs))
    )
    habits = habits_result.scalars().all()

    today = datetime.now().date()
    best_current_streak = 0
    for habit in habits:
        log_dates = [log.log_date for log in habit.logs]
        current, _ = calculate_streaks(log_dates, today)
        best_current_streak = max(best_current_streak, current)

    # Розклад: скільки подій у найближчі 7 днів
    now = datetime.now()
    upcoming_count = (
        await session.execute(
            select(func.count(ScheduleEvent.id)).where(
                ScheduleEvent.user_id == current_user.id,
                ScheduleEvent.start_time >= now,
                ScheduleEvent.start_time <= now + timedelta(days=7),
            )
        )
    ).scalar_one()

    return StatsOverview(
        tasks_total=tasks_total,
        tasks_completed=tasks_completed,
        tasks_pending=tasks_pending,
        habits_total=len(habits),
        best_current_streak=best_current_streak,
        upcoming_events=upcoming_count,
    )