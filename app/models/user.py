from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import EmailStr, Field


class UserRole(str, Enum):
    resident = "resident"
    admin = "admin"


class User(Document):
    name: str
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.resident
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"