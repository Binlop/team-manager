from typing import TYPE_CHECKING
import enum
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, UniqueConstraint, CheckConstraint

from db.session import Base
from auth.models import User

if TYPE_CHECKING:
    from tasks.models import Task, Comment

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"

class TeamRole(str, enum.Enum):
    MEMBER = "member"
    MANAGER = "manager"
    ADMIN = "admin"

class Team(Base):
    __tablename__ = "team"


    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    invite_code: Mapped[str] = mapped_column(String(6), unique=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"))

    manager: Mapped["User"] = relationship(foreign_keys=[manager_id], back_populates="managed_teams")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team")
    tasks: Mapped[list["Task"]] = relationship(back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_member"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_user_team"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"))
    role: Mapped[TeamRole] = mapped_column(
        Enum(TeamRole, name="team_role_enum", values_callable=lambda x: [e.value for e in x]),
        default=TeamRole.MEMBER
    )

    user: Mapped["User"] = relationship(back_populates="team_memberships")
    team: Mapped["Team"] = relationship(back_populates="members")

class Meeting(Base):
    __tablename__ = "meeting"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_meeting_valid_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    organizer_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"), index=True)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status", values_callable=lambda x: [e.value for e in x]), default=MeetingStatus.SCHEDULED
    )
    
    organizer: Mapped["User"] = relationship(back_populates="organized_meetings")
    participants: Mapped[list["UserMeeting"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(
        secondary="user_meetting",
        viewonly=True,
    )

class UserMeeting(Base):
    __tablename__ = "user_meetting"
    __table_args__ = (
        UniqueConstraint("user_id", "meeting_id", name="uq_user_meeting"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id", ondelete="CASCADE"), index=True)

    user: Mapped["User"] = relationship(back_populates="meetings")
    meeting: Mapped["Meeting"] = relationship(back_populates="participants")