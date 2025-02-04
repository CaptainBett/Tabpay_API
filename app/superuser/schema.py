from pydantic import BaseModel, EmailStr
from datetime import datetime


class SuperuserCreate(BaseModel):
    email: EmailStr
    password: str
    
class AdminResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    is_approved: bool
    registered_at: datetime

    class Config:
        from_attributes = True
    
