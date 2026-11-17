from fastapi import APIRouter, status
from teams.schemas import TeamBase, TeamUpdate, TeamMemberCreate, TeamMemberUpdate, TeamMemberRead, TeamRead, MeetingCreate, MeetingUpdate, MeetingRead, UserMeetingCreate, UserMeetingRead
from teams import schemas
from teams.deps import TeamServiceDep, TeamRepoDep, TeamMemberServiceDep, MeetingServiceDep, TeamServiceDep
from api.deps import UserDep


team_router = APIRouter(prefix="/team", tags=["Teams"])
meeting_router = APIRouter(prefix="/meeting", tags=["Meeting"])

@team_router.post("/", response_model=schemas.TeamWithInviteCode, status_code=201)
async def create_team(data: TeamBase, service: TeamServiceDep, user: UserDep):
    return await service.create_team(data, user)

@team_router.get("/{team_id}", response_model=schemas.TeamRead)
async def get_team(team_id: int, service: TeamServiceDep, user: UserDep):
    return await service.get_team_or_404(team_id, user)

@team_router.get("/{team_id}/join/{invite_code}", response_model=TeamMemberRead, status_code=status.HTTP_200_OK)
async def join_team(team_id: int, invite_code: str, service: TeamMemberServiceDep, user: UserDep):
    return await service.add_member_by_invite_code(invite_code, user)

@team_router.get("/{team_id}/members", response_model=list[TeamMemberRead], status_code=status.HTTP_200_OK)
async def get_team_members(team_id: int, service: TeamServiceDep, user: UserDep):
    return await service.get_team_members(team_id, user)

@team_router.put("/{team_id}", response_model=TeamUpdate, status_code=status.HTTP_200_OK)
async def update_team(
    team_id: int, 
    data: TeamUpdate, 
    service: TeamServiceDep,
    user: UserDep
):
    return await service.update_team(team_id, data, user)


@team_router.put("/{team_id}/refresh-invite-code", response_model=schemas.TeamWithInviteCode)
async def refresh_team_invite_code(team_id: int, service: TeamServiceDep, user: UserDep):
    return await service.refresh_invite_code(team_id, user)

@team_router.post("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    team_id: int, 
    data: TeamMemberCreate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.add_member(team_id, data, user)

@team_router.put("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_200_OK)
async def update_member_role(
    team_id: int, 
    data: TeamMemberUpdate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.update_member_role(team_id, data, user)

@team_router.delete("/{team_id}/member", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    team_id: int, 
    user_id: int, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.remove_member(team_id, user_id, user)

@meeting_router.post("/", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def create_meeting(data: MeetingCreate, service: MeetingServiceDep, user: UserDep):
    return await service.create_meeting(data, user)

@meeting_router.post("/add-participant", response_model=UserMeetingRead, status_code=status.HTTP_201_CREATED)
async def add_meeting_member(data: UserMeetingCreate, service: MeetingServiceDep, user: UserDep):
    return await service.add_user_to_meeting(data, user)

@meeting_router.get("/my-meetings", response_model=list[MeetingRead], status_code=status.HTTP_200_OK)
async def get_user_meetings(service: MeetingServiceDep, user: UserDep):
    return await service.get_user_meetings(user)

@meeting_router.put("/{meeting_id}/", response_model=MeetingRead, status_code=status.HTTP_200_OK)
async def update_meeting(
    meeting_id: int,
    data: MeetingUpdate,
    service: MeetingServiceDep, 
    user: UserDep
):
    return await service.update_meeting(data, user)

@meeting_router.delete("/{meeting_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: int, 
    service: MeetingServiceDep, 
    user: UserDep
):
    return await service.delete_meeting(meeting_id, user)




