from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SocialApp"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./social.db"

    JWT_SECRET: str = "please_change_me"
    JWT_ALG: str = "HS256"
    JWT_ACCESS_EXPIRES: int = 3600  # seconds

    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

settings = Settings()
