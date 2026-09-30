from pydantic import BaseModel


class StatsOverview(BaseModel):
    tasks_total: int
    tasks_completed: int
    tasks_pending: int
    habits_total: int
    best_current_streak: int
    upcoming_events: int