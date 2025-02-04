from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User, UserRole
from.schema import Token, AdminCreate, AdminResponse
from ..utils import hash_password, verify_password
from sqlalchemy import select
from .Oauth2 import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register/admin", response_model=AdminResponse)
async def register_admin(
    admin: AdminCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if email exists    
    existing_email = await db.execute(
        select(User).where((User.email == admin.email))
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = hash_password(admin.password)
    new_admin = User(
        **admin.dict(exclude={"password"}),
        password=hashed_password,
        role=UserRole.ADMIN,
        is_approved=False  # Requires superuser approval
    )
    
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(),db: AsyncSession = Depends(get_db)):
    user = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = user.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Additional check for admin approval
    if user.role == UserRole.ADMIN and not user.is_approved:
        raise HTTPException(status_code=403, detail="Admin account pending approval")
    
    return {
        "access_token": create_access_token({"sub": user.email}),
        "token_type": "bearer"
    }




    

    