from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from auth.exceptions import InvalidTokenError
from auth.schemas import UserCreate, TokenResponse, UserRead, UserLogin, RefreshTokenRequest
from api.deps import UserServiceDep, UserDep, TokenServiceDep

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: UserServiceDep):
    return await service.register(data)

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login_json(
    data: UserLogin, 
    service: UserServiceDep,
):
    return await service.login(data)

@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login_form(service: UserServiceDep, form: OAuth2PasswordRequestForm = Depends()):
    data = UserLogin(identifier=form.username.lower(), password=form.password)
    return await service.login(data)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    service: UserServiceDep,
    refresh_token: str,
):
    if not refresh_token:
        raise InvalidTokenError()
    cmd = RefreshTokenRequest(refresh_token=refresh_token)
    await service.logout(cmd)

@router.post("/refresh_token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    service: TokenServiceDep,
    refresh_token: str,
):
    if not refresh_token:
        raise InvalidTokenError()
    data = RefreshTokenRequest(refresh_token=refresh_token)
    return await service.update_refresh_token(data)
    
@router.get("/me", status_code=status.HTTP_200_OK)
async def get_user(user: UserDep):
    return user.username