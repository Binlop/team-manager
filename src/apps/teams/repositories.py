from sqlalchemy import select, delete, update, exists
from sqlalchemy.orm import selectinload, joinedload
from db.uow import UnitOfWork
from teams.models import Team, TeamMember
from teams.schemas import TeamCreate, TeamMemberCreate, TeamMemberUpdate

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

    async def update_team(self, team_id: int, team: TeamCreate) -> Team | None:
        stmt = (
            update(Team)
            .where(Team.id == team_id)
            .values(
                name=team.name,
                invite_code=team.invite_code,
                manager_id=team.manager_id,
            )
            .returning(Team)
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