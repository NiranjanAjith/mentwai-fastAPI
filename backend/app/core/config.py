"""
Core configuration management for the AI Tutor service.
Loads environment variables and provides centralized settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'test_database')
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
    AZURE_OPENAI_KEY: str = os.environ.get('AZURE_OPENAI_KEY', '')
    AZURE_OPENAI_VERSION: str = os.environ.get('AZURE_OPENAI_VERSION', '2024-02-15-preview')
    OPENAI_TIMEOUT: int = int(os.environ.get('OPENAI_TIMEOUT', 30))
    OPENAI_MAX_RETRIES: int = int(os.environ.get('OPENAI_MAX_RETRIES', 3))
    
    # Redis Configuration
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    REDIS_POOL_SIZE: int = int(os.environ.get('REDIS_POOL_SIZE', 15))
    REDIS_DEFAULT_TTL: int = int(os.environ.get('REDIS_DEFAULT_TTL', 600))
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS: int = int(os.environ.get('MAX_CONCURRENT_REQUESTS', 50))
    CONTEXT_RETRIEVAL_TIMEOUT: int = int(os.environ.get('CONTEXT_RETRIEVAL_TIMEOUT', 100))
    CLASSIFICATION_TIMEOUT: int = int(os.environ.get('CLASSIFICATION_TIMEOUT', 200))
    VECTOR_SEARCH_TIMEOUT: int = int(os.environ.get('VECTOR_SEARCH_TIMEOUT', 80))

settings = Settings()