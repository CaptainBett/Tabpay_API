from pydantic import BaseModel
from datetime import datetime
from ..models import Member

class MemberBase(BaseModel):
    full_name: str
    image_file: str | None = None

class MemberCreate(MemberBase):
    phone_number: str
    id_number: str
    acc_number: str


class MemberResponse(MemberBase):
    id: int
    registered_at: datetime
    phone_number: str
    id_number: str
    acc_number: str
    block_id: int  
    zone_id: int   

    @classmethod
    def from_member_with_association(cls, member: Member):
        association = member.block_associations[0]
        return cls(
            **member.__dict__,
            phone_number=association.phone_number,
            id_number=association.id_number,
            acc_number=association.acc_number,
            block_id=association.block_id,
            zone_id=association.zone_id
        )
