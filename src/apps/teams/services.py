from datetime import datetime
from teams.models import Team, TeamMember, TeamRole, Meeting, UserMeeting
from teams.repositories import TeamRepository, TeamMemberRepository, MeetingRepository
from teams.schemas import TeamCreate, TeamMemberCreate, TeamMemberUpdate, MeetingCreate, MeetingUpdate, UserMeetingCreate
from teams.exceptions import TeamNotFoundError, InviteCodeAlreadyExistsError, TeamMemberNotFoundError, TeamMemberAlreadyExistsError, CannotRemoveManagerError, MeetingNotFoundError
from teams import exceptions
from auth.models import User
from auth.repositories import UserRepository
from auth.exceptions import UserNotFoundError
from core.exceptions import PermissionDeniedError

class TeamService:

    def __init__(
            self,
            team_repo: TeamRepository,
            user_repo: UserRepository,
    ) -> None:
        self.team_repo = team_repo
        self.user_repo = user_repo

    async def get_team_members(self, team_id: int) -> list[TeamMember]:
        team_members = await self.team_repo.get_team_members(team_id=team_id)
        return team_members

    async def create_team(self, data: TeamCreate) -> Team:
        team = await self.team_repo.get_team_by_invite_code(data.invite_code)
        if team is not None:
            raise InviteCodeAlreadyExistsError(invite_code=data.invite_code)
        manager = await self.user_repo.get_by_user_id(data.manager_id)
        if manager is None:
            raise UserNotFoundError(model_object_id=data.manager_id)
        return await self.team_repo.create_team(data)

    async def update_team(self, team_id: int, data: TeamCreate, manager_id: User) -> Team | None:
        team = await self.team_repo.get_team_by_id(team_id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        new_manager = await self.user_repo.get_by_user_id(data.manager_id)
        if new_manager is None:
            raise UserNotFoundError(model_object_id=data.manager_id)
        if team.manager_id != manager_id.id:
            raise PermissionDeniedError()
        team = await self.team_repo.update_team(team_id=team_id, team=data)
        return team

class TeamMemberService:

    def __init__(
            self,
            team_repo: TeamRepository,
            team_member_repo: TeamMemberRepository,
    ) -> None:
        self.team_repo = team_repo
        self.team_member_repo = team_member_repo

    async def add_member(self, data: TeamMemberCreate, manager: User) -> TeamMember:
        team = await self.team_repo.get_team_by_id(data.team_id)
        if team is None:
            raise TeamNotFoundError(model_object_id=data.team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        is_member_exists = await self.team_member_repo.check_member_exists_with_user_id_and_team_id(
            data.user_id,
            data.team_id,
        )
        if is_member_exists is True:
            raise TeamMemberAlreadyExistsError(user_id=data.user_id, team_id=data.team_id)
        created_member = await self.team_member_repo.add_team_member(data)
        member = await self.team_member_repo.get_member_by_id(member_id=created_member.id)
        if member is None:
            raise TeamMemberNotFoundError(created_member.id)
        return member

    async def update_member_role(self, data: TeamMemberUpdate, manager: User):
        team = await self.team_repo.get_team_by_id(data.team_id)
        if team is None:
            raise TeamNotFoundError(model_object_id=data.team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        updated = await self.team_member_repo.update_member_role(member=data)
        if updated is None:
            raise TeamMemberNotFoundError(model_object_id=data.id)
        if updated.role == 'manager' and updated.id != manager.id:
            previous_manager = await self.team_member_repo.get_member_by_team_and_user_id(team_id=updated.team_id, user_id=manager.id)
            if previous_manager is None:
                raise TeamMemberNotFoundError(model_object_id=manager.id)
            data_to_update_previous_manager = TeamMemberUpdate(id=previous_manager.id, team_id=updated.team_id, role=TeamRole.MEMBER)
            await self.team_member_repo.update_member_role(member=data_to_update_previous_manager)
        member = await self.team_member_repo.get_member_by_id(updated.id)
        return member

    async def remove_member(self, team_id: int, user_id: int, manager: User):
        team = await self.team_repo.get_team_by_id(team_id)
        if team is None:
            raise TeamNotFoundError(model_object_id=team_id)
        if team.manager_id != manager.id:
            raise PermissionDeniedError()
        member = await self.team_member_repo.get_member_by_team_and_user_id(team_id, user_id)
        if member is None:
            raise TeamMemberNotFoundError(user_id)
        if member.role == 'manager' or member.role == 'admin':
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
        is_participant_exists = self.user_repo.check_user_exists(data.participant_id)
        if not is_participant_exists:
            raise UserNotFoundError(data.participant_id)
        is_meeting_conflict = await self.meeting_repo.check_user_meeting_conflicts(meeting.starts_at, meeting.ends_at, user.id)
        if is_meeting_conflict:
            raise exceptions.MeetingTimeConflictError(meeting.starts_at, meeting.ends_at)
        created = await self.meeting_repo.add_user_to_meeting(meeting.id, data.participant_id)
        user_meeting = await self.meeting_repo.get_user_meeting(created.id)
        if user_meeting is None:
            raise exceptions.UserMeetingNotFoundError(created.id)
        return user_meeting

    async def get_user_meetings(self, user: User) -> list[Meeting]:
        meetings = await self.meeting_repo.get_user_meetings(user.id)
        return meetings

    async def get_calendar_events(self, starts_at: datetime, ends_at: datetime, user: User):
        meetings = await self.meeting_repo.get_user_meetings_in_time(starts_at, ends_at, user.id)
        tasks = await self.meeting_repo.get_user_meetings_in_time(starts_at, ends_at, user.id)