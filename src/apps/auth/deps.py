from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from db.uow import UnitOfWork, get_uow
from auth.repositories import UserRepository, TokenRepository
from auth.services import UserService, TokenService
from core.cache import CacheDep

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_user_repository(uow: UnitOfWork = Depends(get_uow)) -> UserRepository:
    return UserRepository(uow)

def get_token_repository(uow: UnitOfWork = Depends(get_uow)) -> TokenRepository:
    return TokenRepository(uow)

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepoDep = Annotated[TokenRepository, Depends(get_token_repository)]

def get_user_service(
        user_repository: UserRepoDep,
        token_repository: TokenRepoDep,
        cache: CacheDep,
    ) -> UserService:
    return UserService(user_repository, token_repository, cache)

def get_token_service(uow: UnitOfWork = Depends(get_uow)) -> TokenService:
    return TokenService(uow)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]

TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]