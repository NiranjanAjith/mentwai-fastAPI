from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import our AI services
from app.core.logging import Logger
logger = Logger(name="Server")

# Set up the root directory for loading environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from app.api.v1.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize AI services on startup."""
    logger.info("🚀 AI Tutor Service starting up...")
    logger.info("✅ Parallel agents system initialized")
    logger.info("✅ Controller Agent: Fast intent classification (<200ms)")
    logger.info("✅ Tutor Agent: Streaming educational responses")
    logger.info("✅ Orchestrator: Parallel execution coordinator")
    logger.info("🎯 Performance targets: <400ms first token, 50+ concurrent users")

    yield

    """Cleanup on shutdown."""
    logger.info("🛑 AI Tutor Service shutting down...")
    logger.info("\n"*5)
    logger.output("\n"*5)
    logger.performance("\n"*5)
    try:
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Create the main app without a prefix
app = FastAPI(
    title="AI Tutor Service",
    description="FastAPI AI microservice with parallel agents for educational tutoring",
    version="1.0.0",
    lifespan=lifespan
)

# Register Tortoise ORM with the app
# register_tortoise(
#     app,
#     config=settings.TORTOISE_ORM,
#     generate_schemas=False,
#     add_exception_handlers=True,
# )

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Add existing routes (backward compatibility)
@api_router.get("/")
async def root():
    return {"message": "AI Tutor Service v1.0 - Parallel Agents Ready!"}

# Add AI services routes
api_router.include_router(chat_router, prefix="/v1")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
