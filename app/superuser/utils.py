from sqlalchemy.future import select
from ..models import User, UserRole
from ..database import async_session
from ..config import settings
from ..utils import hash_password


async def create_initial_superuser():
    """Create superuser during application startup if not exists"""
    async with async_session() as db:
        # Check if superuser already exists
        result = await db.execute(
            select(User).where(
                (User.email == settings.superuser_email) |
                (User.role == UserRole.SUPERUSER)
            )
        )
        existing_superuser = result.scalar_one_or_none()
        
        if existing_superuser:
            print("Superuser already exists. Skipping creation.")
            return

        # Validate credentials exist
        if not settings.superuser_email or not settings.superuser_password:
            print("Superuser credentials not found in .env. Skipping creation.")
            return

        # Create new superuser
        try:
            hashed_password = hash_password(settings.superuser_password)
            superuser = User(
                email=settings.superuser_email,
                password=hashed_password,
                role=UserRole.SUPERUSER,
                is_approved=True,
                is_active=True
            )
            
            db.add(superuser)
            await db.commit()
            print("Superuser created successfully")
            
        except Exception as e:
            await db.rollback()
            print(f"Error creating superuser: {str(e)}")
            raise