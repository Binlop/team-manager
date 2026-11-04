from typing import Annotated
from fastapi import Depends, Request, Query
from core.cache import RedisCache
from dataclasses import dataclass
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from core.security import verify_token
from core.exceptions import PermissionDeniedError
from auth.exceptions import InvalidTokenError
from db.uow import UnitOfWork, get_uow
from auth.repositories import UserRepository, TokenRepository
from auth.services import UserService, TokenService
from auth.models import User
from structlog.contextvars import bind_contextvars

def get_cache(request: Request) -> RedisCache:
    return RedisCache(request.app.state.redis)


CacheDep = Annotated[RedisCache, Depends(get_cache)]

@dataclass
class Pagination:
    limit: int = 10
    offset: int = 0

def get_pagination(
        limit: int = Query(10, ge=1, le=100, description="Сколько записей вернуть"),
        offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)

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

PaginationDep = Annotated[Pagination, Depends(get_pagination)]

async def get_current_user(
    repo: UserRepoDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = verify_token(token, expected_type="access")
    if payload is None:
        raise InvalidTokenError()
    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError()   
    try:
        sub = int(sub)
    except Exception as e:
        raise InvalidTokenError()
    user = await repo.get_by_user_id(id=sub)
    if not user or not user.is_active:
        raise InvalidTokenError()
    bind_contextvars(user_id=user.id)
    return user

UserDep = Annotated[User, Depends(get_current_user)]

async def require_superuser(user: UserDep) -> User:
    if not user.is_superuser:
        raise PermissionDeniedError("Superuser privileges required")
    return user

OnlyAdmin = Annotated[User, Depends(require_superuser)]