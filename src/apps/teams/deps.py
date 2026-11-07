from typing import Annotated
from fastapi import Depends
from db.uow import get_uow
from teams.repositories import TeamRepository, TeamMemberRepository, MeetingRepository
from teams.services import TeamService, TeamMemberService, MeetingService
from auth.deps import UserRepoDep

def get_team_repository(uow=Depends(get_uow)) -> TeamRepository:
    return TeamRepository(uow)

def get_team_member_repository(uow=Depends(get_uow)) -> TeamMemberRepository:
    return TeamMemberRepository(uow)

def get_meeting_repository(uow=Depends(get_uow)) -> MeetingRepository:
    return MeetingRepository(uow)

TeamRepoDep = Annotated[TeamRepository, Depends(get_team_repository)]
TeamMemberRepoDep = Annotated[TeamMemberRepository, Depends(get_team_member_repository)]
MeetingRepoDep = Annotated[MeetingRepository, Depends(get_meeting_repository)]

def get_team_service(
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> TeamService:
    return TeamService(team_repo=team_repo, user_repo=user_repo)

def get_team_member_service(
    team_repo: TeamRepoDep,
    team_member_repo: TeamMemberRepoDep,
) -> TeamMemberService:
    return TeamMemberService(
        team_repo=team_repo,
        team_member_repo=team_member_repo,
    )

def get_meeting_service(
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> MeetingService:
    return MeetingService(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]
TeamMemberServiceDep = Annotated[TeamMemberService, Depends(get_team_member_service)]
MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]