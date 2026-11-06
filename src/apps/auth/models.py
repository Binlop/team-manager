from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime
from db.session import Base


if TYPE_CHECKING:
    from teams.models import Team, TeamMember, Meeting, UserMeeting
    from tasks.models import Task, Comment

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), default="Иван", comment="Имя")
    last_name: Mapped[str] = mapped_column(String(100), default="Иванов", comment="Фамилия")
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    managed_teams: Mapped[list["Team"]] = relationship(back_populates="manager", foreign_keys="Team.manager_id")
    team_memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")
    tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")
    organized_meetings: Mapped[list["Meeting"]] = relationship(back_populates="organizer")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="user")


class Token(Base):
    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(default=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)