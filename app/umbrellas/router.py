from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Umbrella
from .schema import UmbrellaCreate, UmbrellaResponse
from ..auth.Oauth2 import get_current_admin
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
