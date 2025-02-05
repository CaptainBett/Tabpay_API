from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Umbrella, UserRole
from .schema import UmbrellaCreate, UmbrellaResponse
from ..auth.Oauth2 import get_current_admin, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/umbrellas", tags=["Umbrellas"])

@router.post("/create-umbrella", response_model=UmbrellaResponse)
async def create_umbrella(
    umbrella: UmbrellaCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # current_admin.umbrella is now eagerly loaded in get_current_admin.
    if current_admin.umbrella:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already has an umbrella"
        )

    # Create new umbrella
    new_umbrella = Umbrella(
        name=umbrella.name,
        location=umbrella.location,
        admin_id=current_admin.id
    )
    
    db.add(new_umbrella)
    await db.commit()
    await db.refresh(new_umbrella)
    
    # Re-query the umbrella to eagerly load the 'blocks' relationship.
    result = await db.execute(
        select(Umbrella)
        .options(selectinload(Umbrella.blocks))
        .where(Umbrella.id == new_umbrella.id)
    )
    umbrella_with_blocks = result.scalar_one_or_none()
    
    return umbrella_with_blocks

#TODO Add try except blocks



@router.get("/umbrellas/", response_model=list[UmbrellaResponse])
async def get_all_umbrellas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # For superusers, return all umbrellas
    if current_user.role == UserRole.SUPERUSER:
        result = await db.execute(
            select(Umbrella)
            .options(selectinload(Umbrella.blocks))
            .order_by(Umbrella.created_at)
        )
        return result.scalars().all()
    
    # For admins, return their own umbrella
    umbrella = current_user.umbrella
    if not umbrella:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No umbrella found for this admin"
        )
    
    # Reload with blocks relationship
    result = await db.execute(
        select(Umbrella)
        .options(selectinload(Umbrella.blocks))
        .where(Umbrella.id == umbrella.id)
    )
    return [result.scalar_one()]

@router.get("/umbrellas/{umbrella_id}", response_model=UmbrellaResponse)
async def get_umbrella_by_id(
    umbrella_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get umbrella with blocks
    result = await db.execute(
        select(Umbrella)
        .options(selectinload(Umbrella.blocks))
        .where(Umbrella.id == umbrella_id)
    )
    umbrella = result.scalar_one_or_none()
    
    if not umbrella:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Umbrella not found"
        )
    
    # Authorization check
    if current_user.role == UserRole.ADMIN:
        user_umbrella = current_user.umbrella
        if not user_umbrella or user_umbrella.id != umbrella_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this umbrella"
            )
    
    return umbrella