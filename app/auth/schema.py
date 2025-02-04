from pydantic import BaseModel, EmailStr
from datetime import datetime


class AdminResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    is_approved: bool
    registered_at: datetime

    class Config:
        from_attributes = True


class AdminCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

    
class TokenData(BaseModel):
    email: EmailStr | None = None
