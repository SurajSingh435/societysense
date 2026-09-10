from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.resident


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    model_config = {"populate_by_name": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"