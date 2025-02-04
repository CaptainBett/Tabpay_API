from pydantic import BaseModel
from datetime import datetime

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

    class Config:
        from_attributes = True