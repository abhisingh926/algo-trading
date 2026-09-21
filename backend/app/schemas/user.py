from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(ORMModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class AuthStatus(BaseModel):
    auth_enabled: bool
    registration_open: bool
    has_users: bool
