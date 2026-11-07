from datetime import datetime
from core.exceptions import DomainError, NotFoundError

class TeamNotFoundError(NotFoundError):
    model_name = "Team"

class TeamMemberNotFoundError(NotFoundError):
    model_name = "TeamMember"

class InviteCodeAlreadyExistsError(DomainError):
    status_code = 409
    error_code = "invite_code_already_exists"

    def __init__(self, invite_code: str):
        self.invite_code = invite_code
        super().__init__(f"Invite code {invite_code} already exists")

class TeamMemberAlreadyExistsError(DomainError):
    status_code = 409
    error_code = "team_member_already_exists"

    def __init__(self, user_id: int, team_id: int):
        self.user_id = user_id
        self.team_id = team_id
        super().__init__(f"Team member with user {self.user_id} and team {team_id} already exists")

class CannotRemoveManagerError(DomainError):
    status_code = 409
    error_code = "cannot_remove_manager"

    def __init__(self, team_id: int, user_id: int) -> None:
        self.team_id = team_id
        self.user_id = user_id
        super().__init__(
            f"Cannot remove user {user_id} from team {team_id}: "
            f"team must have at least one manager"
        )

class MeetingNotFoundError(NotFoundError):
    model_name = "Meeting"

class UserMeetingNotFoundError(NotFoundError):
    model_name = "UserMeeting"

class MeetingTimeConflictError(DomainError):
    status_code = 409
    error_code = "meeting_time_conflict"

    def __init__(self, starts_at: datetime, ends_at: datetime):
        super().__init__(f"The user already has a meeting scheduled during time interval from {starts_at} to {ends_at}")