from typing import Annotated
from pydantic import StringConstraints
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.config.errors import ErrorMessages


# 회원가입
class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[
        str,
        StringConstraints(min_length=6, max_length=20)
    ]
    password_confirm: str
    company_id: int = Field(..., ge=1, le=5)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        if not (has_letter and has_number):
            raise ValueError(ErrorMessages.PASSWORD_COMPLEXITY)
        return v

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    company_id: int

    class Config:
        from_attributes = True


# 로그인
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"