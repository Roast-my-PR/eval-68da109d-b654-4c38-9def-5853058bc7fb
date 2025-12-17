import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/lever_xpert")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-12345")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-2")

    AIRFLOW_BASE_URL: str = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
    AIRFLOW_USERNAME: str = os.getenv("AIRFLOW_USERNAME", "admin")
    AIRFLOW_PASSWORD: str = os.getenv("AIRFLOW_PASSWORD", "admin")

    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
