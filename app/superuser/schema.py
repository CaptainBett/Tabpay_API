from pydantic import BaseModel, EmailStr


class SuperuserCreate(BaseModel):
    email: EmailStr
    password: str
    
