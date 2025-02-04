from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User,UserRole
from .schema import SuperuserCreate
from sqlalchemy import select
from ..utils import hash_password
from ..auth.Oauth2 import get_current_superuser
from .schema import AdminResponse 


router = APIRouter(prefix="/superuser", tags=["Superuser"])


@router.get("/pending-admins/", response_model=list[AdminResponse])
async def get_pending_admins(
    db: AsyncSession = Depends(get_db),
    superuser: User = Depends(get_current_superuser)
):
    result = await db.execute(
        select(User).where(
            User.role == UserRole.ADMIN,
            User.is_approved == False
        )
    )
    pending_admins = result.scalars().all()  
    return pending_admins


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