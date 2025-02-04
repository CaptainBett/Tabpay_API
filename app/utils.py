from passlib.context import CryptContext
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .config import settings


SQLALCHEMY_DATABASE_URL = settings.db_url


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    echo=True
)

async_session = async_sessionmaker(
    engine, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    hashed_password = pwd_context.hash(password)
    return hashed_password

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
