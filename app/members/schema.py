from pydantic import BaseModel
from datetime import datetime
from ..models import Member

class MemberBase(BaseModel):
    full_name: str
    bank_id: int

class Bank(BaseModel):
    id: int
    name:str
    
    class Config:
        from_attributes = True
        
class MemberCreate(MemberBase):
    phone_number: str
    id_number: str
    acc_number: str


class MemberBlockAssociationResponse(BaseModel):
    block_id: int
    zone_id: int
    phone_number: str
    id_number: str
    acc_number: str

    class Config:
        from_attributes = True

class MemberResponse(BaseModel):
    id: int
    full_name: str
    bank: Bank
    registered_at: datetime
    associations: list[MemberBlockAssociationResponse]

    @classmethod
    def from_member(cls, member: Member):
        return cls(
            id=member.id,
            full_name=member.full_name,
            bank=member.bank,
            registered_at=member.registered_at,
            associations=[
                MemberBlockAssociationResponse(
                    block_id=assoc.block_id,
                    zone_id=assoc.zone_id,
                    phone_number=assoc.phone_number,
                    id_number=assoc.id_number,
                    acc_number=assoc.acc_number
                )
                for assoc in member.block_associations
            ]
        )
    
class MemberUpdate(BaseModel):
    full_name: str | None = None
    bank_id: int | None = None
    phone_number: str | None = None
    id_number: str | None = None
    acc_number: str | None = None
    zone_id: int | None = None
