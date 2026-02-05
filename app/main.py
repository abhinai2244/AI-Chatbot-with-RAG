from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router
from app.core.database import engine, Base
# Import models to ensure they are registered with Base metadata
from app.models import db_models
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the FastAPI application.
    
    Startup:
    --------
    - Initializes the database connection.
    - Creates tables if they do not exist (syncs schema).
    
    Shutdown:
    ---------
    - Clean up resources (if any).
    """
    logger.info("Starting up application...")
    async with engine.begin() as conn:
        # Create all tables defined in models
        # In production, we would use Alembic for migrations, 
        # but for this assignment, `create_all` is sufficient.
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created.")
    
    yield
    
    logger.info("Shutting down application...")

app = FastAPI(
    title="AI Chatbot API",
    description="Backend API for an AI Chatbot with RAG and Session Management.",
    version="1.0.0",
    lifespan=lifespan
)

# Register API Router
# All routes will be prefixed with /api
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    """
    Root endpoint to verify the service is running.
    """
    return {"message": "Welcome to the AI Chatbot API. Check /docs for Swagger UI."}
