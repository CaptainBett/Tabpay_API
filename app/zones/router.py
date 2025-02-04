from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Zone, Block
from .schema import ZoneCreate, ZoneResponse
from ..auth.Oauth2 import get_current_admin
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