from fastapi import APIRouter, Depends, HTTPException, status, Response
from ..database import get_db
from ..models import User, Zone, Block, Member, MemberBlockAssociation, UserRole
from .schema import MemberCreate, MemberResponse, MemberUpdate
from ..auth.Oauth2 import get_current_admin, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
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

    # Create member core record
    new_member = Member(
        full_name=member.full_name,
        bank_id=member.bank_id
    )
    db.add(new_member)
    await db.flush()

    # Create first association
    association = MemberBlockAssociation(
        member_id=new_member.id,
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
            status_code=400,
            detail="Duplicate member details in block"
        )

    # Return full member data
    result = await db.execute(
        select(Member)
        .options(selectinload(Member.block_associations))
        .where(Member.id == new_member.id)
    )
    return MemberResponse.from_member(result.scalar_one())

@router.post("/{member_id}/add-to-block/", response_model=MemberResponse)
async def add_to_block(
    member_id: int,
    zone_id: int,
    phone_number: str,
    id_number: str,
    acc_number: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Validate zone and block ownership
    result = await db.execute(
        select(Zone)
        .join(Block)
        .where(
            Zone.id == zone_id,
            Block.parent_umbrella_id == current_admin.umbrella.id
        )
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=403, detail="Unauthorized zone")

    # Get existing member with associations
    result = await db.execute(
        select(Member)
        .options(selectinload(Member.block_associations))
        .where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Check if already in block
    if any(a.block_id == zone.parent_block_id for a in member.block_associations):
        raise HTTPException(
            status_code=400,
            detail="Member already in this block"
        )

    # Create new association
    new_association = MemberBlockAssociation(
        member_id=member_id,
        block_id=zone.parent_block_id,
        zone_id=zone_id,
        phone_number=phone_number,
        id_number=id_number,
        acc_number=acc_number
    )

    try:
        db.add(new_association)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Duplicate details in block or already exists in block"
        )

    # Return updated member data
    result = await db.execute(
        select(Member)
        .options(
            selectinload(Member.block_associations),
            selectinload(Member.bank)
        )
        .where(Member.id == member_id)
    )
    updated_member = result.scalar_one()
    
    return MemberResponse.from_member(updated_member)

#TODO Add try except blocks

@router.get("/", response_model=list[MemberResponse])
async def get_all_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # For superusers: return all members with their associations
    if current_user.role == UserRole.SUPERUSER:
        result = await db.execute(
            select(Member)
            .options(
                selectinload(Member.block_associations),
                selectinload(Member.bank)  # Eager load bank relationship
            )
            .order_by(Member.registered_at)
        )
        members = result.scalars().all()
        return [MemberResponse.from_member(member) for member in members]

    # For admins: return only members associated with blocks in admin's umbrella
    if current_user.role == UserRole.ADMIN:
        if not current_user.umbrella:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No umbrella found for this admin"
            )
        
        result = await db.execute(
            select(Member)
            .join(MemberBlockAssociation)
            .join(Block)
            .where(Block.parent_umbrella_id == current_user.umbrella.id)
            .options(
                selectinload(Member.block_associations),
                selectinload(Member.bank)  # Eager load bank relationship
            )
        )
        members = result.scalars().unique().all()
        return [MemberResponse.from_member(member) for member in members]

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
        .options(
            selectinload(Member.block_associations),            
            selectinload(Member.bank)
)
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

    return MemberResponse.from_member(member)



@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    member_data: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Fetch member along with its associations and bank data
    result = await db.execute(
        select(Member)
        .options(
            selectinload(Member.block_associations),
            selectinload(Member.bank)
        )
        .where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Verify member belongs to an admin-approved block (umbrella)
    valid_blocks_result = await db.execute(
        select(Block.id)
        .where(Block.parent_umbrella_id == current_admin.umbrella.id)
    )
    valid_block_ids = valid_blocks_result.scalars().all()
    
    if not any(assoc.block_id in valid_block_ids for assoc in member.block_associations):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_dict = member_data.dict(exclude_unset=True)
    
    # Update core member fields (e.g., full_name, bank_id)
    for field in ['full_name', 'bank_id']:
        if field in update_dict:
            setattr(member, field, update_dict[field])
    
    # Update association fields if provided
    if any(field in update_dict for field in ['phone_number', 'id_number', 'acc_number', 'zone_id']):
        # Find the first association that is part of the valid blocks
        association = next(
            (assoc for assoc in member.block_associations if assoc.block_id in valid_block_ids),
            None
        )
        if not association:
            raise HTTPException(status_code=404, detail="Member association not found")
        
        # Validate and update zone_id if it's provided
        if 'zone_id' in update_dict and update_dict['zone_id'] is not None:
            new_zone_id = update_dict['zone_id']
            zone = await db.get(Zone, new_zone_id)
            if not zone:
                raise HTTPException(status_code=400, detail=f"Zone with id {new_zone_id} does not exist")
            association.zone_id = new_zone_id
        
        # Update the other association fields if provided
        for field in ['phone_number', 'id_number', 'acc_number']:
            if field in update_dict and update_dict[field] is not None:
                setattr(association, field, update_dict[field])
        
        # Check that the updated association details are unique within the block
        stmt = select(MemberBlockAssociation).where(
            MemberBlockAssociation.block_id == association.block_id,
            or_(
                MemberBlockAssociation.phone_number == association.phone_number,
                MemberBlockAssociation.id_number == association.id_number,
                MemberBlockAssociation.acc_number == association.acc_number
            ),
            MemberBlockAssociation.member_id != member_id
        )
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Duplicate details in block")
    
    try:
        await db.commit()
        # Re-fetch the updated member with relationships
        result = await db.execute(
            select(Member)
            .options(
                selectinload(Member.block_associations),
                selectinload(Member.bank)
            )
            .where(Member.id == member_id)
        )
        updated_member = result.scalar_one()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database error during commit")
    
    # Return the updated member using the conversion method defined on MemberResponse
    return MemberResponse.from_member(updated_member)



@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Fetch member with relationships
    result = await db.execute(
        select(Member)
        .options(
            selectinload(Member.block_associations),
            selectinload(Member.contributions)
        )
        .where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Verify member belongs to an admin-approved block (umbrella)
    valid_blocks_result = await db.execute(
        select(Block.id)
        .where(Block.parent_umbrella_id == current_admin.umbrella.id)
    )
    valid_block_ids = valid_blocks_result.scalars().all()
    
    if not any(a.block_id in valid_block_ids for a in member.block_associations):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete member and associations
    await db.delete(member)
    
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete member with existing contributions")

    return Response(status_code=status.HTTP_204_NO_CONTENT)