from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.chat_service import process_chat
from app.services.file_service import process_file
from app.api.schemas import ChatRequest, ChatResponse, UploadResponse
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------------------
# API Routes
# ------------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to perform a chat interaction.
    
    Args:
        request (ChatRequest): Contains 'query' and 'session_id'.
        background_tasks (BackgroundTasks): Used to schedule summarization after response.
        db (AsyncSession): Database session.
    
    Returns:
        ChatResponse: The AI generated response.
    """
    logger.info(f"Chat request received for session: {request.session_id}")
    try:
        response_text = await process_chat(request.session_id, request.query, db, background_tasks)
        return ChatResponse(response=response_text, session_id=request.session_id)
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during chat processing.")

@router.post("/upload", response_model=UploadResponse)
async def upload_endpoint(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to upload a file (PDF or Text) for context.
    
    Args:
        file (UploadFile): The file to be uploaded.
        session_id (str): The session to associate the file with.
        db (AsyncSession): Database session.
        
    Returns:
        UploadResponse: Confirmation of success.
    
    Raises:
        HTTPException: If file processing fails.
    """
    logger.info(f"Upload request received for session: {session_id}, filename: {file.filename}")
    try:
        await process_file(file, session_id, db)
        return UploadResponse(
            filename=file.filename if file.filename else "unknown",
            session_id=session_id,
            message="File uploaded and processed successfully."
        )
    except HTTPException as he:
        # Re-raise known HTTP exceptions (from file_service)
        raise he
    except Exception as e:
        logger.error(f"Error in upload_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during file upload.")
