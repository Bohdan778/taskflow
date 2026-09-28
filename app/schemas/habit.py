from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class HabitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class HabitLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_date: date


class HabitWithLogs(HabitRead):
    logs: list[HabitLogRead]
    
class HabitStats(BaseModel):
    habit_id: int
    total_logs: int
    current_streak: int
    longest_streak: int
    done_today: bool