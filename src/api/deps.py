from typing import Annotated
from fastapi import Depends, Query
from dataclasses import dataclass
from typing import Annotated
from core.security import verify_token
from core.exceptions import PermissionDeniedError
from auth.exceptions import InvalidTokenError
from auth.deps import oauth2_scheme, UserRepoDep
from auth.models import User
from structlog.contextvars import bind_contextvars

@dataclass
class Pagination:
    limit: int = 10
    offset: int = 0

def get_pagination(
        limit: int = Query(10, ge=1, le=100, description="Сколько записей вернуть"),
        offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)

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