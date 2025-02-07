from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Zone, Block, UserRole
from .schema import ZoneCreate, ZoneResponse, ZoneUpdate
from ..auth.Oauth2 import get_current_admin, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/zones", tags=["Zones"])

@router.post("/create-zone", response_model=ZoneResponse)
async def create_zone(
    zone: ZoneCreate,
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Verify block belongs to admin's umbrella
    block = await db.get(Block, block_id)
    if not block or block.parent_umbrella_id != current_admin.umbrella.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found"
        )

    new_zone = Zone(
        name=zone.name,
        parent_block_id=block_id
    )
    
    db.add(new_zone)
    await db.commit()
    await db.refresh(new_zone)
    
    # Re-query the zone with eager loading of both members and parent_block
    result = await db.execute(
        select(Zone)
        .options(
            selectinload(Zone.members),
            selectinload(Zone.parent_block)
        )
        .where(Zone.id == new_zone.id)
    )
    zone_with_members = result.scalar_one_or_none()
    return zone_with_members


#TODO Add try except blocks


@router.get("/", response_model=list[ZoneResponse])
async def get_all_zones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Eagerly load both parent_block and members
    options = [selectinload(Zone.parent_block), selectinload(Zone.members)]
    
    if current_user.role == UserRole.SUPERUSER:
        result = await db.execute(
            select(Zone)
            .options(*options)
            .order_by(Zone.created_at)
        )
        return result.scalars().all()

    # For admins, return zones only within their umbrella's blocks
    if not current_user.umbrella:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No umbrella found for this admin"
        )

    result = await db.execute(
        select(Zone)
        .options(*options)
        .join(Block)
        .where(Block.parent_umbrella_id == current_user.umbrella.id)
    )
    return result.scalars().all()


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone_by_id(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Zone)
        .options(
            selectinload(Zone.parent_block),
            selectinload(Zone.members)
        )
        .where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )

    # Authorization: Admins can only access their own zones
    if current_user.role == UserRole.ADMIN:
        block = await db.get(Block, zone.parent_block_id)
        if not block or block.parent_umbrella_id != current_user.umbrella.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this zone"
            )

    return zone



# Update Zone

@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone_data: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Zone)
        .options(
            selectinload(Zone.parent_block).selectinload(Block.parent_umbrella),
            selectinload(Zone.members)  # Eagerly load members to avoid lazy loading during response serialization
        )
        .where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    if current_user.role == UserRole.ADMIN and current_user.id != zone.parent_block.parent_umbrella.admin_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this zone")
    
    # Check for name uniqueness within the same block
    existing = await db.execute(
        select(Zone)
        .where(Zone.name == zone_data.name, Zone.parent_block_id == zone.parent_block_id, Zone.id != zone_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Zone name already exists in this block")
    
    zone.name = zone_data.name
    
    try:
        await db.commit()
        await db.refresh(zone)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
    
    return zone

# Delete Zone
@router.delete("/{zone_id}")
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Zone)
        .options(selectinload(Zone.members))
        .where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    if current_user.role == UserRole.ADMIN and current_user.id != zone.parent_block.parent_umbrella.admin_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this zone")
    
    if zone.members:
        raise HTTPException(status_code=400, detail="Cannot delete zone with existing members. Remove members first.")
    
    await db.delete(zone)
    
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete zone due to database constraints")
    
    return {"message": "Zone deleted successfully"}