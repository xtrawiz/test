from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_ID: int
    API_HASH: str
    BOT_TOKEN: str
    DATABASE_URL: str  # e.g., mysql+aiomysql://user:pass@host:port/db_name
    REDIS_URL: str     # e.g., redis://localhost:6379/0
    LOG_LEVEL: str = "INFO"
    FASTAPI_SECRET_KEY: str = "YOUR_DEFAULT_FASTAPI_SECRET_KEY" # Should be overridden by env var in production
    CELERY_TASK_ALWAYS_EAGER: bool = False # Useful for testing

    class Config:
        env_file = ".env" # In a real scenario, you'd have a .env file or set these in the environment
        env_file_encoding = 'utf-8'

settings = Settings()
