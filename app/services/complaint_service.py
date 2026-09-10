from app.models.complaint import Complaint, ComplaintStatus
from app.models.user import User
from app.schemas.complaint import ComplaintCreate
from app.services.ai_service import triage_complaint
from app.services.embedding_service import get_embedding, find_possible_duplicate
from app.core.config import settings

 
async def create_complaint(data: ComplaintCreate, resident: User) -> Complaint:
    triage_result = await triage_complaint(data.description, data.category)

    complaint = Complaint(
        resident_id=resident,
        category=triage_result["category"],
        description=data.description,
        ai_title=triage_result["title"],
        ai_urgency=triage_result["urgency"],
        ai_reasoning=triage_result["reasoning"],
    )
    await complaint.insert()

    embedding = await get_embedding(data.description)
    if embedding:
        complaint.embedding = embedding
        match = await find_possible_duplicate(
            embedding,
            triage_result["category"],
            exclude_id=complaint.id,
            threshold=settings.duplicate_similarity_threshold,
        )
        if match:
            duplicate_complaint = await Complaint.get(match["complaint_id"])
            if duplicate_complaint:
                complaint.duplicate_of = duplicate_complaint
                complaint.similarity_score = match["similarity"]
        await complaint.save()

    return complaint


async def get_my_complaints(resident: User) -> list[Complaint]:
    return await Complaint.find(Complaint.resident_id.id == resident.id).to_list()



async def get_all_complaints() -> list[Complaint]:
    return await Complaint.find_all().to_list()



async def update_status(complaint_id: str, new_status: ComplaintStatus) -> Complaint | None:
    complaint = await Complaint.get(complaint_id)
    if not complaint:
        return None
    complaint.status = new_status
    await complaint.save()
    return complaint