"""
app/api/pages.py — server-rendered HTML pages (Jinja2 + HTMX).

These routes are separate from the JSON API (app/api/auth.py,
app/api/complaints.py). Browser pages read JWT from a cookie,
while API clients can continue using Authorization headers.
"""

from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from jose import JWTError, jwt

from app.core.config import settings
from app.core.templates import templates
from app.models.user import User, UserRole
from app.models.complaint import ComplaintStatus
from app.services.auth_service import verify_password, create_access_token
from app.schemas.complaint import ComplaintCreate
from app.services import complaint_service


router = APIRouter(prefix="/pages", tags=["pages"])


async def get_current_user_from_cookie(request: Request) -> User | None:
    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        user_id = payload.get("sub")

        if not user_id:
            return None

    except JWTError:
        return None

    return await User.get(user_id)


def render_complaint_card(c) -> str:
    duplicate_html = ""

    if c.duplicate_of:
        pct = round((c.similarity_score or 0) * 100)

        duplicate_html = (
            f'<p style="color: orange;">'
            f'⚠ Possible duplicate ({pct}% similar)'
            f'</p>'
        )

    return f"""
    <div class="complaint-card" id="complaint-{c.id}">
        <strong>{c.ai_title or c.description}</strong>
        <p>
            Category: {c.category} |
            Status: {c.status} |
            Urgency: {c.ai_urgency}
        </p>
        {duplicate_html}
    </div>
    """


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    user = await User.find_one(User.email == email)

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid email or password",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    response = RedirectResponse(
        url="/pages/dashboard",
        status_code=status.HTTP_302_FOUND,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await get_current_user_from_cookie(request)

    if not user:
        return RedirectResponse(
            url="/pages/login",
            status_code=status.HTTP_302_FOUND,
        )

    if user.role == UserRole.admin:
        complaints = await complaint_service.get_all_complaints()

        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "complaints": complaints,
            },
        )

    complaints = await complaint_service.get_my_complaints(user)

    return templates.TemplateResponse(
        request=request,
        name="resident_dashboard.html",
        context={
            "complaints": complaints,
        },
    )


@router.post("/complaints", response_class=HTMLResponse)
async def submit_complaint(
    request: Request,
    category: str = Form(...),
    description: str = Form(...),
):
    user = await get_current_user_from_cookie(request)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    complaint = await complaint_service.create_complaint(
        ComplaintCreate(
            category=category,
            description=description,
        ),
        user,
    )

    return HTMLResponse(
        content=render_complaint_card(complaint)
    )



@router.get("/logout")
async def logout():
    response = RedirectResponse(
        url="/pages/login",
        status_code=status.HTTP_302_FOUND,
    )

    response.delete_cookie("access_token")

    return response



@router.patch(
    "/complaints/{complaint_id}/status",
    response_class=HTMLResponse,
)
async def change_status_page(
    request: Request,
    complaint_id: str,
    status_value: str = Form(..., alias="status"),
):
    user = await get_current_user_from_cookie(request)

    if not user or user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        new_status = ComplaintStatus(status_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid complaint status",
        )

    complaint = await complaint_service.update_status(
        complaint_id,
        new_status,
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return HTMLResponse(
        content=render_complaint_card(complaint)
    )