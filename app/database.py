from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import AsyncGenerator
from .utils import Base, async_session, SQLALCHEMY_DATABASE_URL, engine
from fastapi import FastAPI
from .banks.utils import import_initial_banks
from contextlib import asynccontextmanager
from .superuser.utils import create_initial_superuser



SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL

# Create the async engine
engine = engine

# Create a sessionmaker for AsyncSession
async_session = async_session

# Base class for models
Base = Base



# Dependency for getting the DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# Asynchronous function to create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Import initial data
    await import_initial_banks()

    # Create superuser
    await create_initial_superuser()
    
    yield
