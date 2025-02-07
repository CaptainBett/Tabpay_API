from pydantic import BaseModel
from datetime import datetime

class BlockResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UmbrellaCreate(BaseModel):
    name: str
    location: str

class UmbrellaResponse(BaseModel):
    id: int
    name: str
    location: str
    created_at: datetime
    blocks: list[BlockResponse] = []

    class Config:
        from_attributes = True

class UmbrellaUpdate(BaseModel):
    name: str | None = None
    location: str | None = None

UmbrellaResponse.update_forward_refs()



