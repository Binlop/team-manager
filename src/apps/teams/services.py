import hmac, hashlib, secrets
import string
from datetime import datetime
from teams.models import Team, TeamMember, TeamRole, Meeting, UserMeeting
from teams.repositories import TeamRepository, TeamMemberRepository, MeetingRepository
from teams.schemas import TeamBase, TeamUpdate, TeamRead, TeamWithInviteCode, TeamMemberCreate, TeamMemberUpdate, MeetingCreate, MeetingUpdate, UserMeetingCreate
from teams.exceptions import TeamNotFoundError, TeamMemberNotFoundError, TeamMemberAlreadyExistsError, CannotRemoveManagerError, MeetingNotFoundError
from teams import exceptions
from auth.models import User
from auth.repositories import UserRepository
from auth.exceptions import UserNotFoundError
from core.exceptions import PermissionDeniedError
from core.config import settings

def hash_invite_code(invite_code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        invite_code.encode(),
        hashlib.sha256,
    ).hexdigest()

class TeamService:

    def __init__(
            self,
            team_repo: TeamRepository,
            user_repo: UserRepository,
    ) -> None:
        self.team_repo = team_repo
        self.user_repo = user_repo

    async def get_team_or_404(self, team_id: int, user: User) -> TeamRead:
        """Альтернатива get_team_or_404: DTO без invite_code (и без его хеша)."""
        team = await self.team_repo.get_team_for_user(team_id, user.id)
        if team is None:
            raise exceptions.TeamNotFoundError(team_id)
        return TeamRead.model_validate(team)

    async def get_team_members(self, team_id: int, user: User) -> list[TeamMember]:
        team = await self.team_repo.get_team_for_user(team_id, user.id)
        if team is None:
            raise exceptions.TeamNotFoundError(team_id)
        team_members = await self.team_repo.get_team_members(team_id=team_id, user_id=user.id)
        return team_members

    async def create_team(
        self, data: TeamBase, user: User
    ) -> TeamWithInviteCode:
        """Альтернатива create_team: возвращает команду и raw-код приглашения."""
        invite_code = self.generate_invite_code()
        invite_code_hash = hash_invite_code(invite_code)
        created = await self.team_repo.create_team(data, user.id, invite_code_hash)
        team = await self.team_repo.get_team_for_user(created.id, user.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=created.id)
        return TeamWithInviteCode(
            **TeamRead.model_validate(team).model_dump(),
            invite_code=invite_code,
        )
    
    async def update_team(self, team_id: int, data: TeamUpdate, manager: User) -> Team | None:
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        updated = await self.team_repo.update_team(team_id, data, manager.id)
        if updated is None:
            raise TeamNotFoundError(model_object_id=team_id)
        team = await self.team_repo.get_team_for_user(updated.id, manager.id)
        return team

    async def refresh_invite_code(
        self, team_id: int, manager: User
    ) -> TeamWithInviteCode:
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        invite_code = self.generate_invite_code()
        invite_code_hash = hash_invite_code(invite_code)
        updated = await self.team_repo.update_invite_code_team(team_id, invite_code_hash, manager.id)
        if updated is None:
            raise TeamNotFoundError(model_object_id=team_id)
        
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        return TeamWithInviteCode(
            **TeamRead.model_validate(team).model_dump(),
            invite_code=invite_code,
        )
    
    @staticmethod
    def generate_invite_code(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

class TeamMemberService:

    def __init__(
            self,
            team_repo: TeamRepository,
            team_member_repo: TeamMemberRepository,
    ) -> None:
        self.team_repo = team_repo
        self.team_member_repo = team_member_repo

    async def add_member(self, team_id: int, data: TeamMemberCreate, manager: User) -> TeamMember:
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        is_member_exists = await self.team_member_repo.check_member_exists_with_user_id_and_team_id(
            data.user_id,
            team_id,
        )
        if is_member_exists is True:
            raise TeamMemberAlreadyExistsError(user_id=data.user_id, team_id=team_id)
        created_member = await self.team_member_repo.add_team_member(data, team_id)
        member = await self.team_member_repo.get_member_by_id(member_id=created_member.id)
        if member is None:
            raise TeamMemberNotFoundError(created_member.id)
        return member

    async def add_member_by_invite_code(self, invite_code: str, user: User) -> TeamMember:
        hashed_invite_code = hash_invite_code(invite_code)
        team = await self.team_repo.get_team_by_invite_code(hashed_invite_code)
        if team is None:
            raise exceptions.InvalidInviteCodeError("Invalid invitation code")
        
        is_member_exists = await self.team_member_repo.check_member_exists_with_user_id_and_team_id(
            user.id,
            team.id,
        )
        if is_member_exists is True:
            raise TeamMemberAlreadyExistsError(user_id=user.id, team_id=team.id)
        
        data = TeamMemberCreate(user_id=user.id)
        created_member = await self.team_member_repo.add_team_member(data, team.id)
        member = await self.team_member_repo.get_member_by_id(member_id=created_member.id)
        if member is None:
            raise TeamMemberNotFoundError(created_member.id)
        return member

    async def update_member_role(self, team_id: int, data: TeamMemberUpdate, manager: User):
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        
        manager_member = await self.team_member_repo.get_member_by_team_and_user_id(team_id, manager.id)
        if manager_member is None:
            raise PermissionDeniedError()
        if manager_member.role == TeamRole.MEMBER and manager_member.user_id == manager.id:
            raise exceptions.CannotDemoteManagerError()
        
        updated = await self.team_member_repo.update_member_role(member=data, team_id=team_id)
        if updated is None:
            raise TeamMemberNotFoundError(model_object_id=data.id)
        
        if updated.role == TeamRole.MANAGER and updated.user_id != manager.id:
            previous_manager = await self.team_member_repo.get_member_by_team_and_user_id(team_id=updated.team_id, user_id=manager.id)
            if previous_manager is None:
                raise TeamMemberNotFoundError(model_object_id=manager.id)
            data_to_update_previous_manager = TeamMemberUpdate(id=previous_manager.id, role=TeamRole.MEMBER)
            await self.team_member_repo.update_member_role(member=data_to_update_previous_manager, team_id=team_id)
            await self.team_repo.update_team_manager(team_id=team_id, manager_id=updated.user_id)
        member = await self.team_member_repo.get_member_by_id(updated.id)
        if member is None or member.team_id != team_id:
            raise TeamMemberNotFoundError(model_object_id=data.id)
        return member

    async def remove_member(self, team_id: int, user_id: int, manager: User):
        team = await self.team_repo.get_team_for_user(team_id, manager.id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        member = await self.team_member_repo.get_member_by_team_and_user_id(team_id, user_id)
        if member is None:
            raise TeamMemberNotFoundError(user_id)
        if member.role == TeamRole.MANAGER or member.role == TeamRole.ADMIN:
            raise CannotRemoveManagerError(team_id, user_id)
        is_removed = await self.team_member_repo.remove_member(user_id=user_id, team_id=team_id)
        if not is_removed:
            raise TeamMemberNotFoundError(model_object_id=user_id)


class MeetingService:

    def __init__(
            self,
            meeting_repo: MeetingRepository,
            user_repo: UserRepository,
    ) -> None:
        self.meeting_repo = meeting_repo
        self.user_repo = user_repo

    async def create_meeting(self, data: MeetingCreate, user: User) -> Meeting:
        is_meeting_conflict = await self.meeting_repo.check_user_meeting_conflicts(data.starts_at, data.ends_at, user.id)
        if is_meeting_conflict:
            raise exceptions.MeetingTimeConflictError(data.starts_at, data.ends_at) 
        created = await self.meeting_repo.create_meeting(data, user.id)
        user_meeting_new = await self.meeting_repo.add_user_to_meeting(created.id, user.id)
        meeting = await self.meeting_repo.get_meeting_by_id(created.id, user.id)
        if meeting is None:
            raise MeetingNotFoundError(created.id)
        return meeting

    async def add_user_to_meeting(self, data: UserMeetingCreate, user: User) -> UserMeeting:
        meeting = await self.meeting_repo.get_meeting_by_id(data.meeting_id, user.id)
        if meeting is None:
            raise MeetingNotFoundError(data.meeting_id)
        if meeting.organizer_id != user.id:
            raise PermissionDeniedError()
        is_participant_exists = await self.user_repo.check_user_exists(data.participant_id)
        if not is_participant_exists:
            raise UserNotFoundError(data.participant_id)
        is_meeting_conflict = await self.meeting_repo.check_user_meeting_conflicts(meeting.starts_at, meeting.ends_at, data.participant_id)
        if is_meeting_conflict:
            raise exceptions.ParticipantTimeConflictError(meeting.starts_at, meeting.ends_at)
        created = await self.meeting_repo.add_user_to_meeting(meeting.id, data.participant_id)
        user_meeting = await self.meeting_repo.get_user_meeting(created.id)
        if user_meeting is None:
            raise exceptions.UserMeetingNotFoundError(created.id)
        return user_meeting

    async def get_user_meetings(self, user: User) -> list[Meeting]:
        meetings = await self.meeting_repo.get_user_meetings(user.id)
        return meetings

    async def update_meeting(self, data: MeetingUpdate, user: User) -> Meeting:
        meeting = await self.meeting_repo.get_meeting_by_id(data.id, user.id)
        if meeting is None:
            raise MeetingNotFoundError(data.id)
        if meeting.organizer_id != user.id:
            raise PermissionDeniedError()

        users_id = [user.id for user in meeting.users]
        if users_id:
            busy_users = await self.meeting_repo.get_busy_users(meeting.id, data.starts_at, data.ends_at, users_id)
            if busy_users:
                raise exceptions.ParticipantTimeConflictError(meeting.starts_at, meeting.ends_at)
             
        updated = await self.meeting_repo.update_meeting(data)
        if updated is None:
            raise MeetingNotFoundError(data.id)
        
        user_meeting = await self.meeting_repo.get_meeting_by_id(data.id, user.id)
        if user_meeting is None:
            raise exceptions.UserMeetingNotFoundError(updated.id)
        return user_meeting

    async def delete_meeting(self, meeting_id, user: User):
        meeting = await self.meeting_repo.get_meeting_by_id(meeting_id, user.id)
        if meeting is None:
            raise MeetingNotFoundError(meeting_id)
        if meeting.organizer_id != user.id:
            raise PermissionDeniedError()
        deleted = await self.meeting_repo.delete_meeting(meeting_id, user.id)
        if not deleted:
            raise MeetingNotFoundError(meeting_id)