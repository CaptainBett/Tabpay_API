from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import User, Zone, Block, Member, MemberBlockAssociation, UserRole
from .schema import MemberCreate, MemberResponse
from ..auth.Oauth2 import get_current_admin, get_current_user
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
    new_member = Member(full_name=member.full_name )
    
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



@router.get("/", response_model=list[MemberResponse])
async def get_all_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Adjust if you have a separate dependency for admin
):
    # For superusers: return all members with their associations
    if current_user.role == UserRole.SUPERUSER:
        result = await db.execute(
            select(Member)
            .options(selectinload(Member.block_associations))
            .order_by(Member.registered_at)
        )
        members = result.scalars().all()
        return [MemberResponse.from_member_with_association(member) for member in members]

    # For admins: return only members associated with blocks in admin's umbrella
    if current_user.role == UserRole.ADMIN:
        if not current_user.umbrella:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No umbrella found for this admin"
            )
        # Query members by joining their associations and filtering by the umbrella ID
        result = await db.execute(
            select(Member)
            .join(MemberBlockAssociation)
            .join(Block)
            .where(Block.parent_umbrella_id == current_user.umbrella.id)
            .options(selectinload(Member.block_associations))
        )
        # Using .unique() to avoid duplicate members if they have multiple associations
        members = result.scalars().unique().all()
        return [MemberResponse.from_member_with_association(member) for member in members]

    # If role is not recognized
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access members"
    )


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member_by_id(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Member)
        .options(selectinload(Member.block_associations))
        .where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # For admins, verify that at least one of the member's block associations
    # belongs to a block under the admin's umbrella.
    if current_user.role == UserRole.ADMIN:
        if not current_user.umbrella:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No umbrella found for this admin"
            )
        authorized = False
        # Option 1: Loop over associations (may lead to extra queries if block is not eagerly loaded)
        # Option 2: If you haven't eager loaded Block, you can use a separate query to check authorization.
        for assoc in member.block_associations:
            # We can load the block if not already loaded:
            block = await db.get(Block, assoc.block_id)
            if block and block.parent_umbrella_id == current_user.umbrella.id:
                authorized = True
                break

        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this member"
            )

    return MemberResponse.from_member_with_association(member)