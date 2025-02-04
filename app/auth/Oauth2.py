from sqlalchemy import select
from ..config import settings
from datetime import datetime,timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..models import User, UserRole
from ..database import get_db
from sqlalchemy.orm import selectinload
from .schema import TokenData
from sqlalchemy.ext.asyncio import AsyncSession


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRES_MINUTES = settings.access_token_expires_minutes



# Create Access Token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verify Access Token
async def verify_access_token(token: str, credentials_exception, db: AsyncSession):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == token_data.username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# Get Current User
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials!',
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    user = await verify_access_token(token, credentials_exception, db)
    return user

# Get Current Admin with Eager Loading of Relationships
async def get_current_admin( current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check if the user has admin privileges
    if current_user.role != UserRole.ADMIN or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    # Re-query the user to eagerly load relationships (e.g., umbrella)
    result = await db.execute(
        select(User).options(selectinload(User.umbrella))  # Eagerly load the umbrella relationship
        .where(User.id == current_user.id)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

# Get Current Superuser
async def get_current_superuser(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERUSER:
        raise HTTPException(status_code=403, detail="Superuser privileges required")
    return current_user



