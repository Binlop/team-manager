from datetime import date
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Date, Integer, Enum, CheckConstraint

from db.session import Base
from auth.models import User
from teams.models import Team

class TaskStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class Task(Base):
    __tablename__ = "task"
    __table_args__ = (
        CheckConstraint(
            "status <> 'done' OR (score IS NOT NULL AND manager_comment IS NOT NULL)",
            name="ck_task_done_requires_score_and_comment",
        ),
        CheckConstraint("score IS NULL OR score BETWEEN 1 AND 5", name="ck_task_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Enum(TaskStatus, 
                                             name="status_enum", 
                                             values_callable=lambda x: [e.value for e in x]), 
                                             default=TaskStatus.OPEN
                                        )
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    manager_comment: Mapped[str] = mapped_column(String(500), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship(back_populates="task", order_by="Comment.created_on.asc()")

class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(500))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"), index=True)
    
    author: Mapped["User"] = relationship(back_populates="comments")
    task: Mapped["Task"] = relationship(back_populates="comments")
