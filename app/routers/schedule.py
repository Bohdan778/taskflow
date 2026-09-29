from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ScheduleEvent, User
from app.schemas.schedule import (
    ScheduleEventCreate,
    ScheduleEventRead,
    ScheduleEventUpdate,
)
from app.security import get_current_user

router = APIRouter(prefix="/schedule", tags=["schedule"])


async def get_user_event(
    event_id: int, session: AsyncSession, current_user: User
) -> ScheduleEvent:
    event = await session.get(ScheduleEvent, event_id)
    if event is None or event.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


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
        raise HTTPException(
            status_code=409, detail="This time overlaps with another event"
        )

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


@router.get("/{event_id}", response_model=ScheduleEventRead)
async def get_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_user_event(event_id, session, current_user)


@router.patch("/{event_id}", response_model=ScheduleEventRead)
async def update_event(
    event_id: int,
    data: ScheduleEventUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    event = await get_user_event(event_id, session, current_user)
    updates = data.model_dump(exclude_unset=True)

    new_start = updates.get("start_time", event.start_time)
    new_end = updates.get("end_time", event.end_time)

    if new_end <= new_start:
        raise HTTPException(
            status_code=422, detail="end_time must be after start_time"
        )

    if await has_overlap(
        session, current_user.id, new_start, new_end, exclude_id=event.id
    ):
        raise HTTPException(
            status_code=409, detail="This time overlaps with another event"
        )

    for field, value in updates.items():
        setattr(event, field, value)

    await session.commit()
    await session.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    event = await get_user_event(event_id, session, current_user)
    await session.delete(event)
    await session.commit()