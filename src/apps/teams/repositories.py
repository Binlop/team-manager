from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from db.uow import UnitOfWork
from teams.models import Team, TeamMember
# from .schemas import TeamCreate

class TeamRepository:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow