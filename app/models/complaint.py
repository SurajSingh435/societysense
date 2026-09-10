from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Link
from pydantic import Field

from app.models.user import User


class ComplaintCategory(str, Enum):
    plumbing = "plumbing"
    electrical = "electrical"
    security = "security"
    other = "other"


class ComplaintStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Complaint(Document):
    resident_id: Link[User]
    category: ComplaintCategory
    description: str
    status: ComplaintStatus = ComplaintStatus.open

    # AI fields — filled in later phases, empty for now
    embedding: Optional[list[float]] = None
    ai_title: Optional[str] = None
    ai_urgency: Optional[str] = None
    ai_reasoning: Optional[str] = None
    duplicate_of: Optional[Link["Complaint"]] = None
    similarity_score: Optional[float] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "complaints"