from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

FORBIDDEN_WORDS = {"admin", "root", "superuser", "test"}

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()
    
    @field_validator('username')
    @classmethod
    def username_no_forbidden_words(cls, value: str) -> str:
        if value.lower() in FORBIDDEN_WORDS:
            raise ValueError("Это имя зарезервировано")
        return value.lower()

class UserLogin(BaseModel):
    identifier: str = Field(..., min_length=3)
    password: str

    @field_validator('identifier')
    @classmethod
    def username_no_forbidden_words(cls, value: str) -> str:
        if value.lower() in FORBIDDEN_WORDS:
            raise ValueError("Это имя зарезервировано")
        return value.lower()

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh-token")

    model_config = ConfigDict(from_attributes=True)

