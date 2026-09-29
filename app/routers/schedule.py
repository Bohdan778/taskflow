from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ScheduleEvent, User
from app.schemas.schedule import ScheduleEventCreate, ScheduleEventRead
from app.security import get_current_user

router = APIRouter(prefix="/schedule", tags=["schedule"])


async def has_overlap(
    session: AsyncSession,
    user_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_id: int | None = None,
) -> bool:
    query = select(ScheduleEvent).where(
        ScheduleEvent.user_id == user_id,
        ScheduleEvent.end_time > start_time,
        ScheduleEvent.start_time < end_time,
    )
    if exclude_id is not None:
        query = query.where(ScheduleEvent.id != exclude_id)

    result = await session.execute(query)
    return result.scalars().first() is not None


@router.post("", response_model=ScheduleEventRead, status_code=201)
async def create_event(
    data: ScheduleEventCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if await has_overlap(session, current_user.id, data.start_time, data.end_time):
        raise HTTPException(status_code=409, detail="This time overlaps with another event")

    event = ScheduleEvent(
        title=data.title,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time,
        user_id=current_user.id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@router.get("", response_model=list[ScheduleEventRead])
async def get_events(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ScheduleEvent)
        .where(ScheduleEvent.user_id == current_user.id)
        .order_by(ScheduleEvent.start_time)
    )
    return result.scalars().all()