from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Block
from .schema import BlockResponse, BlockCreate
from ..auth.Oauth2 import get_current_admin
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/blocks", tags=["Blocks"])

@router.post("/create-block", response_model=BlockResponse)
async def create_block(
    block: BlockCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    if not current_admin.umbrella:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin has no umbrella"
        )

    new_block = Block(
        name=block.name,
        parent_umbrella_id=current_admin.umbrella.id
    )
    
    db.add(new_block)
    await db.commit()
    await db.refresh(new_block)
    
    # Re-query the block with eager loading for its 'zones' relationship.
    result = await db.execute(
        select(Block)
        .options(selectinload(Block.zones))
        .where(Block.id == new_block.id)
    )
    block_with_zones = result.scalar_one_or_none()
    return block_with_zones

#TODO Add try except blocks