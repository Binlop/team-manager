import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, UniqueConstraint

from db.session import Base
from auth.models import User

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