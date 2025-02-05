from pydantic import BaseModel
from datetime import datetime


class ZonesResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UmbrellaResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class BlockCreate(BaseModel):
    name: str

class BlockResponse(BaseModel):
    id: int
    name: str
    parent_umbrella: UmbrellaResponse
    created_at: datetime
    zones: list[ZonesResponse] = []

    class Config:
        from_attributes = True

BlockResponse.update_forward_refs()
