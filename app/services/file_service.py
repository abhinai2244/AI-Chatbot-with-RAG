from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Document, DocumentChunk
from app.services.vector_store import get_embeddings_service
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pypdf
import io
import asyncio
import logging

# Configure Logger
logger = logging.getLogger(__name__)

async def process_file(file: UploadFile, session_id: str, db: AsyncSession):
    """
    Handles file upload, text extraction, chunking, and vector embedding.
    
    Steps:
    1. Parse File: Extract text from PDF or TXT.
    2. Save Metadata: Store original file record in DB.
    3. Chunk Text: Split long text into smaller pieces for RAG.
    4. Generate Embeddings: Convert text chunks into vectors.
    5. Save Chunks: Store vectors in pgvector table.
    """
    content = ""
    filename = file.filename if file.filename else "unknown"
    
    # ----------------------------------------------------------------------
    # 1. Parse File
    # ----------------------------------------------------------------------
    try:
        logger.info(f"Processing file: {filename} for session: {session_id}")
        
        if filename.lower().endswith(".pdf"):
            # Read PDF content
            # Note: We use run_in_executor because pypdf is a synchronous CPU-bound task 
            # and could block the async event loop for large files.
            pdf_content = await file.read()
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, parse_pdf, pdf_content)
        elif filename.lower().endswith(".txt"):
            # Read Text content
            content = (await file.read()).decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF and TXT are supported.")
            
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File content is empty or could not be extracted.")

    try:
        # ------------------------------------------------------------------
        # 2. Save Metadata & Original Content
        # ------------------------------------------------------------------
        # We store the full content in `documents` table as a fallback.
        db_doc = Document(session_id=session_id, filename=filename, content=content)
        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)
        
        # ------------------------------------------------------------------
        # 3. Chunking
        # ------------------------------------------------------------------
        # Why 800 characters? 
        # - Good balance between context size and embedding granularity. 
        # - Too small = missing context. Too large = noise.
        # Overlap 100 ensures context isn't lost at cut boundaries.
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = text_splitter.split_text(content)
        
        if not chunks:
            logger.warning(f"No chunks generated for file {filename}")
            return db_doc
        
        # ------------------------------------------------------------------
        # 4. Generate Embeddings
        # ------------------------------------------------------------------
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings_service = get_embeddings_service()
        
        # Batch embedding is more efficient than one by one
        vectors = await embeddings_service.aembed_documents(chunks)
        
        # ------------------------------------------------------------------
        # 5. Save Chunks to DB
        # ------------------------------------------------------------------
        logger.info(f"Saving {len(vectors)} vector chunks to DB...")
        chunk_objects = []
        for chunk_text, vector in zip(chunks, vectors):
            chunk_objects.append(
                DocumentChunk(
                    document_id=db_doc.id,
                    content=chunk_text,
                    embedding=vector
                )
            )
        
        # Bulk insert for performance
        db.add_all(chunk_objects)
        await db.commit()
        
        logger.info("File processing complete.")
        return db_doc
        
    except Exception as e:
        logger.error(f"Error processing document logic: {e}")
        await db.rollback() # Ensure DB consistency
        raise HTTPException(status_code=500, detail=f"Internal Server Error processing file: {str(e)}")

def parse_pdf(content: bytes) -> str:
    """
    Helper to extract text from PDF bytes.
    Run in executor to avoid blocking.
    """
    text = ""
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    except Exception as e:
        logger.error(f"PDF Parsing error: {e}")
    return text
