from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Block, UserRole
from .schema import BlockResponse, BlockCreate
from ..auth.Oauth2 import get_current_admin, get_current_user
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



@router.get("/", response_model=list[BlockResponse])
async def get_all_blocks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Superusers get all blocks
    if current_user.role == UserRole.SUPERUSER:
        result = await db.execute(
            select(Block)
            .options(selectinload(Block.zones))
            .order_by(Block.created_at)
        )
        return result.scalars().all()

    # Admins get only blocks belonging to their umbrella
    if not current_user.umbrella:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No umbrella found for this admin"
        )

    result = await db.execute(
        select(Block)
        .options(selectinload(Block.zones))
        .where(Block.parent_umbrella_id == current_user.umbrella.id)
    )
    return result.scalars().all()


@router.get("/{block_id}", response_model=BlockResponse)
async def get_block_by_id(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Block)
        .options(selectinload(Block.zones))
        .where(Block.id == block_id)
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found"
        )

    # Authorization: Admins can only access their own blocks
    if current_user.role == UserRole.ADMIN and block.parent_umbrella_id != current_user.umbrella.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this block"
        )

    return block

