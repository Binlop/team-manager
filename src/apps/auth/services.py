from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from core.security import create_access_token, create_refresh_token, verify_token
from db.uow import UnitOfWork
from auth.models import User
from auth.exceptions import UserNotFoundError, InvalidCredentialsError, EmailAlreadyExistsError, UsernameAlreadyExistsError, UserAlreadyDeletedError, InvalidTokenError
from auth.repositories import UserRepository, TokenRepository
from auth.schemas import UserCreate, UserLogin, TokenResponse, RefreshTokenRequest
from core.cache import RedisCache

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserService:

    USER_LABS_NAME_CACHE_TTL = int(timedelta(hours=1).total_seconds())

    def __init__(
            self, 
            user_repository: UserRepository,
            token_repository: TokenRepository,
            cache: RedisCache,
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.cache = cache

    async def register(self, data: UserCreate) -> User:
        if await self.user_repository.get_by_email(data.email):
            raise EmailAlreadyExistsError(data.email)
        if await self.user_repository.get_by_username(data.username):
            raise UsernameAlreadyExistsError(data.username)

        user = await self.user_repository.create_user(data)
        return user

    async def login(self, cmd: UserLogin) -> TokenResponse:
        if "@" in cmd.identifier:
            user = await self.user_repository.get_by_email(cmd.identifier)
        else:
            user = await self.user_repository.get_by_username(cmd.identifier)
        if not user or not pwd_context.verify(secret=cmd.password, hash=user.hashed_password):
            raise InvalidCredentialsError()
        data_to_token = {'sub': str(user.id)}

        access_token = create_access_token(data_to_token)
        refresh_token, jti, expires_at = create_refresh_token(data_to_token)
        await self.token_repository.save_refresh_token(jti=jti, 
                                                       user_id=user.id, 
                                                       expires_at=expires_at
                                                       )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    async def delete(self, user_id: int) -> None:
        user = await self.user_repository.get_by_user_id(id=user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        if not user.is_active:
            raise UserAlreadyDeletedError(user_id)
        user.is_active = False

    async def logout(self, data: RefreshTokenRequest):
        payload = verify_token(data.refresh_token, expected_type='refresh') 
        if payload is None:
            raise InvalidTokenError()
        jti = payload["jti"]
        await self.token_repository.revoke_token_by_jti(jti=jti)
        
class TokenService:

    def __init__(self, uow: UnitOfWork):
        self.token_repository = TokenRepository(uow)

    async def update_refresh_token(self, data: RefreshTokenRequest) -> TokenResponse:
        payload = verify_token(data.refresh_token, expected_type='refresh') 
        if payload is None:
            raise InvalidTokenError()

        jti = payload["jti"]
        user_id = int(payload["sub"])

        token = await self.token_repository.get_token_by_jti(jti=jti)
        if not token or token.revoked or token.expires_at < datetime.now(timezone.utc):
            if token and token.revoked:
                await self.token_repository.revoke_all_for_user(user_id=user_id)
            raise InvalidTokenError()

        await self.token_repository.revoke_token_by_jti(jti=jti)
        data_to_token = {'sub': str(user_id)}

        access_token = create_access_token(data_to_token)
        refresh_token, jti, expires_at = create_refresh_token(data_to_token)
        await self.token_repository.save_refresh_token(jti=jti, 
                                                       user_id=user_id, 
                                                       expires_at=expires_at
                                                       )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
