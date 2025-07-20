from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime

# Import our AI services
from app.api.v1.chat import router as chat_router
from app.services.orchestrator import ai_orchestrator
from app.core.config import settings

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="AI Tutor Service",
    description="FastAPI AI microservice with parallel agents for educational tutoring",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models (keeping existing for backward compatibility)
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add existing routes (backward compatibility)
@api_router.get("/")
async def root():
    return {"message": "AI Tutor Service v1.0 - Parallel Agents Ready!"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Add AI services routes
api_router.include_router(chat_router, prefix="/v1")

# Health check for the entire system
@api_router.get("/health")
async def comprehensive_health_check():
    """Comprehensive health check including AI services."""
    try:
        # Check AI orchestrator health
        ai_health = await ai_orchestrator.get_system_health()
        
        # Check database connectivity
        try:
            await db.list_collection_names()
            db_healthy = True
        except Exception:
            db_healthy = False
        
        overall_healthy = ai_health["overall_status"] == "healthy" and db_healthy
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {
                "database": {"status": "connected" if db_healthy else "disconnected"},
                "ai_services": ai_health
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize AI services on startup."""
    logger.info("🚀 AI Tutor Service starting up...")
    logger.info("✅ Parallel agents system initialized")
    logger.info("✅ Controller Agent: Fast intent classification (<200ms)")
    logger.info("✅ Tutor Agent: Streaming educational responses")
    logger.info("✅ Orchestrator: Parallel execution coordinator")
    logger.info("🎯 Performance targets: <400ms first token, 50+ concurrent users")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 AI Tutor Service shutting down...")
    try:
        # Close database connection
        client.close()
        
        # Close Redis connections
        if hasattr(ai_orchestrator.context_service, 'cache'):
            await ai_orchestrator.context_service.cache.close()
        
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
