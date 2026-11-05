from sqlalchemy import select, update, exists
from datetime import datetime, timezone
from passlib.context import CryptContext
from db.uow import UnitOfWork
from auth.models import User, Token
from auth.schemas import UserCreate

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserRepository:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_user(self, data: UserCreate) -> User:
        hashed = pwd_context.hash(data.password)
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hashed,
            first_name=data.first_name,
            last_name=data.last_name,
        )
        self.uow.db.add(user)
        await self.uow.db.flush()
        return user

    async def get_by_email(self, email: str) -> User|None:
        stmt = select(User).where(User.email == email)
        return await self.uow.db.scalar(stmt)

    async def get_by_username(self, username: str) -> User|None:
        stmt = select(User).where(User.username == username)
        return await self.uow.db.scalar(stmt)
    
    async def get_by_user_id(self, id: int) -> User|None:
        stmt = select(User).where(User.id == id)
        return await self.uow.db.scalar(stmt)
    
    async def check_user_exists(self, user_id: int) -> bool:
        stmt = select(
            exists().where(User.id == user_id)
        )
        result = await self.uow.db.execute(stmt)
        return result.scalar_one()


class TokenRepository:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def save_refresh_token(self, jti: str, user_id: int, expires_at: datetime) -> Token:
        token = Token(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.uow.db.add(token)
        return token

    async def get_token_by_jti(self, jti: str):
        stmt = select(Token).where(Token.jti == jti)
        return await self.uow.db.scalar(stmt)

    async def revoke_token(self, token: Token):
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

    async def revoke_token_by_jti(self, jti: str):
        stmt = (update(Token)
                .where(Token.jti == jti)
                .values(
                    revoked = True,
                    revoked_at = datetime.now(timezone.utc)
                ))
        await self.uow.db.execute(stmt) 
       

    async def revoke_all_for_user(self, user_id: int):
        stmt = (
            update(Token)
            .where(
                Token.user_id == user_id,
                Token.revoked == False,
            )
            .values(
                revoked=True,
                revoked_at=datetime.now(timezone.utc),
            )
        )
        await self.uow.db.execute(stmt)