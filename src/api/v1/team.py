from fastapi import APIRouter, status
from teams.schemas import TeamCreate, TeamMemberCreate, TeamMemberUpdate, TeamMemberRead, TeamRead
from teams.deps import TeamServiceDep, TeamRepoDep, TeamMemberServiceDep
from api.deps import UserDep

router = APIRouter(prefix="/team", tags=["Teams"])

@router.post("/", response_model=TeamCreate, status_code=status.HTTP_201_CREATED)
async def create_team(data: TeamCreate, service: TeamServiceDep):
    return await service.create_team(data)

@router.get("/{team_id}", response_model=TeamRead, status_code=status.HTTP_200_OK)
async def get_team(team_id: int, team_repo: TeamRepoDep):
    return await team_repo.get_team_by_id(team_id)

@router.get("/{team_id}/members", response_model=list[TeamMemberRead], status_code=status.HTTP_200_OK)
async def get_team_members(team_id: int, service: TeamServiceDep):
    return await service.get_team_members(team_id)

@router.put("/{team_id}", response_model=TeamCreate, status_code=status.HTTP_200_OK)
async def update_team(
    team_id: int, 
    data: TeamCreate, 
    service: TeamServiceDep,
    user: UserDep
):
    return await service.update_team(team_id, data, user)

@router.post("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    team_id: int, 
    data: TeamMemberCreate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.add_member(data, user)

@router.put("/{team_id}/member", response_model=TeamMemberRead, status_code=status.HTTP_200_OK)
async def update_member_role(
    team_id: int, 
    data: TeamMemberUpdate, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.update_member_role(data, user)

@router.delete("/{team_id}/member", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    team_id: int, 
    user_id: int, 
    service: TeamMemberServiceDep,
    user: UserDep
):
    return await service.remove_member(team_id, user_id, user)
