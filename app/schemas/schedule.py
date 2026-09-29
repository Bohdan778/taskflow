from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ScheduleEventCreate(BaseModel):
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time, info):
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class ScheduleEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime