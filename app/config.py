from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str 
    algorithm: str
    secret_key: str
    access_token_expires_minutes: int
    superuser_email: str
    superuser_password: str

    class Config:
        env_file = ".env"

settings = Settings()