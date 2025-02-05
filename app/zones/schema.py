from pydantic import BaseModel
from datetime import datetime


class BlockResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class MemberResponse(BaseModel):
    id: int
    id_number: str

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
        fields = {"members": {"alias": "member_list"}}

ZoneResponse.update_forward_refs()
