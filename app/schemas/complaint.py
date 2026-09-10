from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.complaint import ComplaintCategory, ComplaintStatus


class ComplaintCreate(BaseModel):
    category: ComplaintCategory
    description: str = Field(..., min_length=5, max_length=1000)


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus


class ComplaintRead(BaseModel):
    id: str = Field(..., alias="_id")
    category: ComplaintCategory
    description: str
    status: ComplaintStatus
    ai_title: Optional[str] = None
    ai_urgency: Optional[str] = None
    created_at: datetime

    model_config = {"populate_by_name": True}