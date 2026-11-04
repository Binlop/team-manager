from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt, ExpiredSignatureError, JWTError
from core.config import settings

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": now,
            'type': 'access'
        })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> tuple[str, str, datetime]:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid4())
    to_encode.update({
            "exp": expires_at,
            "iat": now,
            'jti': jti,
            'type': 'refresh',
        })
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expires_at
     
def verify_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None

    if payload.get("type") != expected_type:
        return None

    return payload