from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Zone, Block, Member, MemberBlockAssociation
from .schema import MemberCreate, MemberResponse
from ..auth.Oauth2 import get_current_admin
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError


router = APIRouter(prefix="/members", tags=["Members"])

@router.post("/add-member/", response_model=MemberResponse)
async def create_member(
    member: MemberCreate,
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Get zone and verify it belongs to admin's umbrella
    zone = await db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )
    
    block = await db.get(Block, zone.parent_block_id)
    if block.parent_umbrella_id != current_admin.umbrella.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this zone"
        )

    # Create member and association
    new_member = Member(
        full_name=member.full_name,
        image_file=member.image_file
    )
    
    association = MemberBlockAssociation(
        phone_number=member.phone_number,
        id_number=member.id_number,
        acc_number=member.acc_number,
        block_id=block.id,
        zone_id=zone_id
    )
    
    db.add(new_member)
    await db.flush()  # Get the member ID before creating association

    # Now create association with the member ID
    association = MemberBlockAssociation(
        member_id=new_member.id,  # Use the flushed ID
        phone_number=member.phone_number,
        id_number=member.id_number,
        acc_number=member.acc_number,
        block_id=block.id,
        zone_id=zone_id
    )
    
    db.add(association)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate member details in block"
        )

    # Eager load relationships
    result = await db.execute(
        select(Member)
        .options(selectinload(Member.block_associations))
        .where(Member.id == new_member.id)
    )
    member_with_assocs = result.scalar_one()

    return MemberResponse.from_member_with_association(member_with_assocs)


#TODO Add try except blocks