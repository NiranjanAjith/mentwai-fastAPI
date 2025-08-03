"""
Core configuration management for the AI Tutor service.
Loads environment variables and provides centralized settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker



# Load environment variables
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings:
    """Application settings loaded from environment variables."""

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    
    # Database Configuration
    DB_URL: str = os.getenv("DATABASE_URL")
    BASE_MODEL_PATH = "app.services.tools.tables"

    MODELS = [
        f"{BASE_MODEL_PATH}.student",
        f"{BASE_MODEL_PATH}.textbook"
    ]
    
    @asynccontextmanager
    async def get_session(self):
        try:
            engine = create_async_engine(Settings.DB_URL, echo=True)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with async_session() as session:
                yield session
        except Exception as e:
            raise RuntimeError(f"Database connection error. (SQLAlchemy Sessionmaker Error: {e})")

    TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": os.getenv("DATABASE_HOST"),
                    "port": os.getenv("DATABASE_PORT"),
                    "user": os.getenv("POSTGRES_USER"),
                    "password": os.getenv("POSTGRES_PASSWORD"),
                    "database": os.getenv("POSTGRES_DB"),
                },
            }
        },
        "apps": {
            "models": {
                "models": MODELS,  # module with your models
                "default_connection": "default",
            }
        }
    }

    #Pinecone Configuration
    PINECONE_API_KEY: str = os.environ.get('PINECONE_API_KEY')
    
    # Azure OpenAI Configuration
    LANGUAGE_MODEL: str = os.environ.get("LANGUAGE_MODEL") # "Llama-3.3-70B-Instruct"
    VISION_MODEL: str = os.environ.get("VISION_MODEL") # "Llama-3.2-90B-Vision-Instruct"

    AZURE_ENDPOINT: str = os.environ.get('AZURE_ENDPOINT')
    AZURE_KEY: str = os.environ.get('AZURE_KEY')
    AZURE_VERSION: str = os.environ.get('AZURE_VERSION')
    AZURE_TIMEOUT: int = int(os.environ.get('AZURE_TIMEOUT', 30))
    AZURE_MAX_RETRIES: int = int(os.environ.get('AZURE_MAX_RETRIES', 3))
    
    # # Redis Configuration
    # REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    # REDIS_POOL_SIZE: int = int(os.environ.get('REDIS_POOL_SIZE', 15))
    # REDIS_DEFAULT_TTL: int = int(os.environ.get('REDIS_DEFAULT_TTL', 600))
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY: str = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION: str = os.environ.get('AWS_REGION')
    AWS_S3_BUCKET_NAME: str = os.environ.get('AWS_S3_BUCKET_NAME')
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS: int = int(os.environ.get('MAX_CONCURRENT_REQUESTS', 50))
    CONTEXT_RETRIEVAL_TIMEOUT: int = int(os.environ.get('CONTEXT_RETRIEVAL_TIMEOUT', 100))
    CLASSIFICATION_TIMEOUT: int = int(os.environ.get('CLASSIFICATION_TIMEOUT', 200))
    VECTOR_SEARCH_TIMEOUT: int = int(os.environ.get('VECTOR_SEARCH_TIMEOUT', 80))
    
    # Logging Configuration
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')


settings = Settings()


def validate_token(token: str) -> bool:
    """Validate JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        return True if payload else False
    except ExpiredSignatureError:
        return False
    except InvalidTokenError:
        return False
