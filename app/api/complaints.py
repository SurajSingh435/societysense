from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintStatusUpdate
from app.services import complaint_service
from app.services.search_service import parse_search_query, build_query

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_complaint(data: ComplaintCreate, current_user: User = Depends(get_current_user)):
    complaint = await complaint_service.create_complaint(data, current_user)
    return {
        "id": str(complaint.id),
        "message": "Complaint submitted successfully",
        "category": complaint.category,
        "ai_title": complaint.ai_title,
        "ai_urgency": complaint.ai_urgency,
        "ai_reasoning": complaint.ai_reasoning,
        "duplicate_of": str(complaint.duplicate_of.id) if complaint.duplicate_of else None,
        "similarity_score": complaint.similarity_score,
    }


@router.get("/my")
async def my_complaints(current_user: User = Depends(get_current_user)):
    complaints = await complaint_service.get_my_complaints(current_user)
    return [
        {
            "id": str(c.id),
            "category": c.category,
            "description": c.description,
            "status": c.status,
            "ai_title": c.ai_title,
            "ai_urgency": c.ai_urgency,
        }
        for c in complaints
    ]


@router.get("/admin/all")
async def all_complaints(admin: User = Depends(require_admin)):
    complaints = await complaint_service.get_all_complaints()
    return [
        {
            "id": str(c.id),
            "category": c.category,
            "description": c.description,
            "status": c.status,
            "ai_title": c.ai_title,
            "ai_urgency": c.ai_urgency,
            "ai_reasoning": c.ai_reasoning,
            "duplicate_of": str(c.duplicate_of.id) if c.duplicate_of else None,
            "similarity_score": c.similarity_score,
        }
        for c in complaints
    ]


@router.get("/admin/search")
async def search_complaints(q: str, admin: User = Depends(require_admin)):
    parsed = await parse_search_query(q)
    query = build_query(parsed)
    complaints = await Complaint.find(query).to_list()
    return [
        {
            "id": str(c.id),
            "category": c.category,
            "description": c.description,
            "status": c.status,
            "ai_title": c.ai_title,
            "ai_urgency": c.ai_urgency,
        }
        for c in complaints
    ]


@router.patch("/admin/{complaint_id}/status")
async def change_status(complaint_id: str, data: ComplaintStatusUpdate, admin: User = Depends(require_admin)):
    complaint = await complaint_service.update_status(complaint_id, data.status)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"id": str(complaint.id), "status": complaint.status}