from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Zone, Block, UserRole
from .schema import ZoneCreate, ZoneResponse
from ..auth.Oauth2 import get_current_admin, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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