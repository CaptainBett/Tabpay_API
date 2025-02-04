from pydantic import BaseModel, EmailStr
from datetime import datetime


class BlockResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class MemberResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

class ZoneCreate(BaseModel):
    name: str

class ZoneResponse(BaseModel):
    id: int
    name: str
    parent_block: BlockResponse
    created_at: datetime
    members: list[MemberResponse] = []

    class Config:
        from_attributes = True

ZoneResponse.update_forward_refs()
