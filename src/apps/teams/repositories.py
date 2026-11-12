from datetime import datetime
from sqlalchemy import select, delete, update, exists, or_
from sqlalchemy.orm import selectinload, joinedload
from db.uow import UnitOfWork
from teams.models import Team, TeamMember, Meeting, UserMeeting, MeetingStatus
from teams.schemas import TeamCreate, TeamUpdate, TeamMemberCreate, TeamMemberUpdate, MeetingCreate,  MeetingUpdate

class TeamRepository:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_team(self, data: TeamCreate) -> Team:
        team = Team(
            name = data.name,
            invite_code = data.invite_code,
            manager_id = data.manager_id,
        )
        self.uow.db.add(team)
        await self.uow.db.flush()

        member = TeamMember(
            user_id = data.manager_id,
            team_id = team.id,
            role = "manager"
        )
        self.uow.db.add(member)
        return team

    async def get_team_by_id(self, team_id: int) -> Team | None:
        stmt = (
            select(Team).where(Team.id == team_id)
            .options(
                joinedload(Team.manager)
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_team_by_invite_code(self, invite_code: str) -> Team | None:
        stmt = select(Team).where(Team.invite_code == invite_code)
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_team_members(self, team_id: int) -> list[TeamMember]:
        stmt = (
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .options(
                joinedload(TeamMember.user),
                joinedload(TeamMember.team),
            )
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())

    async def update_team(self, team_id: int, team: TeamUpdate) -> Team | None:
        stmt = (
            update(Team)
            .where(Team.id == team_id)
            .values(
                name=team.name,
                invite_code=team.invite_code,
            )
            .returning(Team)
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def update_team_manager(self, team_id: int, manager_id: int) -> Team | None:
        stmt = (
            update(Team)
            .where(Team.id == team_id)
            .values(
                manager_id=manager_id,
            ).returning(Team)
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()


class TeamMemberRepository:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_member_by_id(self, member_id: int) -> TeamMember | None:
        stmt = (
            select(TeamMember).where(TeamMember.id == member_id)
            .options(
                joinedload(TeamMember.user),
                joinedload(TeamMember.team),
            )        
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def get_member_by_team_and_user_id(self, team_id: int, user_id: int) -> TeamMember | None:
        stmt = (
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .options(
                joinedload(TeamMember.user),
                joinedload(TeamMember.team),
            )        
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def check_member_exists_with_user_id_and_team_id(self, user_id: int, team_id: int) -> bool:
        stmt = select(
            exists().where(
                TeamMember.user_id == user_id,
                TeamMember.team_id == team_id
            )
        )
        result = await self.uow.db.execute(stmt)
        return result.scalar_one()  

    async def add_team_member(self, member: TeamMemberCreate) -> TeamMember:
        team_member = TeamMember(
            user_id = member.user_id,
            team_id = member.team_id,
            role = member.role,
        )
        self.uow.db.add(team_member)
        await self.uow.db.flush()
        return team_member

    async def remove_member(self, user_id: int, team_id: int) -> bool:
        """Удаляет участника из команды."""
        stmt = delete(TeamMember).where(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id
        )
        result = await self.uow.db.execute(stmt)
        return result.rowcount > 0 # type: ignore

    async def update_member_role(self, member: TeamMemberUpdate) -> TeamMember | None:
        stmt = (
            update(TeamMember)
            .where(TeamMember.id == member.id)
            .values(role=member.role)
            .returning(TeamMember)
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

class MeetingRepository:

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_meeting(self, data: MeetingCreate, user_id: int) -> Meeting:
        meeting = Meeting(
            name = data.name,
            starts_at = data.starts_at,
            ends_at = data.ends_at,
            status = data.status,
            organizer_id = user_id,
        )
        self.uow.db.add(meeting)
        await self.uow.db.flush()
        return meeting

    async def add_user_to_meeting(self, meeting_id, user_id: int) -> UserMeeting:
        user_meeting = UserMeeting(
            user_id = user_id,
            meeting_id = meeting_id,
        )
        self.uow.db.add(user_meeting)
        await self.uow.db.flush()
        return user_meeting

    async def get_meeting_by_id(self, meeting_id: int, user_id: int) -> Meeting | None:
        stmt = (
            select(Meeting)
            .where(
                Meeting.id == meeting_id,
                Meeting.participants.any(UserMeeting.user_id == user_id)
            )
            .options(
                joinedload(Meeting.organizer),
                selectinload(Meeting.users),
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_meetings(self, user_id: int) -> list[Meeting]:
        stmt = (
            select(Meeting)
            .where(
                exists().where(
                    Meeting.id == UserMeeting.meeting_id,
                    UserMeeting.user_id == user_id,
                    Meeting.status == MeetingStatus.SCHEDULED
                )
            )
            .options(
                joinedload(Meeting.organizer),
                selectinload(Meeting.users)
            )
        )    
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())
    
    async def check_user_meeting_conflicts(self, starts_at: datetime, ends_at: datetime, user_id: int) -> bool:
        stmt = (
            select(
                exists().where(
                    Meeting.participants.any(
                        UserMeeting.user_id == user_id
                    ),
                    Meeting.starts_at < ends_at,
                    Meeting.ends_at > starts_at,
                )
            )
        )
        return bool(await self.uow.db.scalar(stmt))

    async def get_user_meeting(self, user_meeting_id: int) -> UserMeeting | None:
        stmt = (
            select(UserMeeting).where(
                UserMeeting.id == user_meeting_id
            )
            .options(
                joinedload(UserMeeting.user),
                joinedload(UserMeeting.meeting),
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def get_user_meetings_in_time(self, starts_at: datetime, ends_at: datetime, user_id: int) -> list[Meeting]:
        stmt = (
            select(Meeting).where(
                Meeting.starts_at < ends_at,
                Meeting.ends_at > starts_at,
                Meeting.participants.any(UserMeeting.user_id == user_id)
            )
            .options(
                joinedload(Meeting.organizer),
                selectinload(Meeting.users),
            )
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())