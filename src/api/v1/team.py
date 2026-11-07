from fastapi import APIRouter, status
from teams.schemas import TeamCreate, TeamMemberCreate, TeamMemberUpdate, TeamMemberRead, TeamRead, MeetingCreate, MeetingUpdate, MeetingRead, UserMeetingCreate, UserMeetingRead
from teams.deps import TeamServiceDep, TeamRepoDep, TeamMemberServiceDep, MeetingServiceDep, MeetingRepoDep
from api.deps import UserDep


team_router = APIRouter(prefix="/team", tags=["Teams"])
meeting_router = APIRouter(prefix="/meeting", tags=["Meeting"])

@team_router.post("/", response_model=TeamCreate, status_code=status.HTTP_201_CREATED)
async def create_team(data: TeamCreate, service: TeamServiceDep):
    return await service.create_team(data)

@team_router.get("/{team_id}", response_model=TeamRead, status_code=status.HTTP_200_OK)
async def get_team(team_id: int, team_repo: TeamRepoDep):
    return await team_repo.get_team_by_id(team_id)

@team_router.get("/{team_id}/members", response_model=list[TeamMemberRead], status_code=status.HTTP_200_OK)
async def get_team_members(team_id: int, service: TeamServiceDep):
    return await service.get_team_members(team_id)

@team_router.put("/{team_id}", response_model=TeamCreate, status_code=status.HTTP_200_OK)
async def update_team(
    team_id: int, 
    data: TeamCreate, 
    service: TeamServiceDep,
    user: UserDep
):
    return await service.update_team(team_id, data, user)

@team_router.post("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    team_id: int, 
    data: TeamMemberCreate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.add_member(data, user)

@team_router.put("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_200_OK)
async def update_member_role(
    team_id: int, 
    data: TeamMemberUpdate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.update_member_role(data, user)

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


