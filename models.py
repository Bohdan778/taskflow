from datetime import date, datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    due_date: Mapped[date]
    priority: Mapped[int] = mapped_column(default=3)
    completed: Mapped[bool] = mapped_column(default=False)
    category: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())