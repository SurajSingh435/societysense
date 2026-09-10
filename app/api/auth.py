from fastapi import APIRouter, HTTPException, status, Depends

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, Token
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    await user.insert()
    return {"message": "User registered successfully"}


@router.post("/login", response_model=Token)
async def login(data: UserLogin):
    user = await User.find_one(User.email == data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=str(user.id), role=user.role)
    return Token(access_token=token)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email, "role": current_user.role}