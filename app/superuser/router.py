from fastapi import APIRouter, HTTPException, Depends,status
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User,UserRole
from .schema import SuperuserCreate
from sqlalchemy import select
from ..utils import hash_password
from ..auth.Oauth2 import get_current_superuser
from ..auth.schema import AdminResponse 


router = APIRouter(prefix="/superuser", tags=["Superuser"])


#TODO CREATE THIS SUPERUSER VIA THE COMMANDLINE OR AUTOMATICALLY

@router.post("/create-superuser/")
async def create_superuser(
    superuser: SuperuserCreate,
    db: AsyncSession = Depends(get_db)
):
    # In real production, protect this endpoint or use CLI-only creation
    existing_superuser = await db.execute(
        select(User).where(
            (User.email == superuser.email) |
            (User.role == UserRole.SUPERUSER)
        )
    )
    if existing_superuser.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Superuser already exists")

    hashed_password = hash_password(superuser.password)
    superuser = User(
        email=superuser.email,
        password=hashed_password,
        role=UserRole.SUPERUSER,
        is_approved=True,
        is_active=True
    )
    
    db.add(superuser)
    await db.commit()
    return {"message": "Superuser created successfully"}

@router.get("/approve-admin/", response_model=list[AdminResponse])
async def get_pending_admins(db: AsyncSession = Depends(get_db), superuser: User = Depends(get_current_superuser)):
    superuser = await db.execute(
        select(User).where(
            (User.email == superuser.email) |
            (User.role == UserRole.SUPERUSER)
        )
    )    
    if superuser:
        pending_admins = await db.execute(
            select(User).where(
                User.role == UserRole.ADMIN,
                User.is_approved == False
            )
        )
        if pending_admins:      
            return pending_admins
    else:
        raise HTTPException(status_code=404,detail="Superuser does not exist")

@router.post("/approve-admin/{admin_id}/", response_model=AdminResponse)
async def approve_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    superuser: User = Depends(get_current_superuser)
):
    superuser = await db.execute(
        select(User).where(
            (User.email == superuser.email) |
            (User.role == UserRole.SUPERUSER)
        )
    ) 
    if superuser:
        user = await db.get(User, admin_id)
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        user.is_approved = True
        await db.commit()
        await db.refresh(user)
        return user
    raise HTTPException(status_code=404,detail="Superuser not found")