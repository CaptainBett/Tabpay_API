from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Umbrella, UserRole
from .schema import UmbrellaCreate, UmbrellaResponse, UmbrellaUpdate
from ..auth.Oauth2 import get_current_admin, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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



@router.get("/", response_model=list[UmbrellaResponse])
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


@router.get("/{umbrella_id}", response_model=UmbrellaResponse)
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


@router.put("/{umbrella_id}", response_model=UmbrellaResponse)
async def update_umbrella(
    umbrella_id: int,
    umbrella_data: UmbrellaUpdate,
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
        raise HTTPException(status_code=404, detail="Umbrella not found")

    # Authorization check
    if current_user.role == UserRole.ADMIN and current_user.id != umbrella.admin_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this umbrella")

    # Update fields
    update_dict = umbrella_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            setattr(umbrella, key, value)

    # Check name uniqueness if changing name
    if 'name' in update_dict:
        existing = await db.execute(
            select(Umbrella)
            .where(Umbrella.name == update_dict['name'], Umbrella.id != umbrella_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Umbrella name already exists")

    try:
        await db.commit()
        # Re-query to ensure all relationships are loaded
        result = await db.execute(
            select(Umbrella)
            .options(selectinload(Umbrella.blocks))
            .where(Umbrella.id == umbrella_id)
        )
        updated_umbrella = result.scalar_one()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")

    return updated_umbrella

@router.delete("/{umbrella_id}")
async def delete_umbrella(
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
        raise HTTPException(status_code=404, detail="Umbrella not found")

    # Authorization check
    if current_user.role == UserRole.ADMIN and current_user.id != umbrella.admin_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this umbrella")

    # Prevent deletion if umbrella has blocks
    if len(umbrella.blocks) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete umbrella with existing blocks. Delete blocks first."
        )

    await db.delete(umbrella)
    
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete umbrella due to database constraints"
        )

    return {"message": "Umbrella deleted successfully"}