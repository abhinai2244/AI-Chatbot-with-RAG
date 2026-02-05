from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

# ------------------------------------------------------------------------------
# Database Models
# ------------------------------------------------------------------------------
# These models define the schema for the chatbot application.
# We use SQLAlchemy for ORM mapping and pgvector for Vector Search capabilities.
# ------------------------------------------------------------------------------

class Session(Base):
    """
    Represents a user session in the chatbot.
    
    Why this table exists:
    ----------------------
    - To group messages and documents under a single conversation context.
    - To maintain a running 'summary' of the conversation which is used for 
      context injection in RAG, ensuring the LLM "remembers" long conversations 
      without exceeding context limits.
    """
    __tablename__ = "sessions"

    # Primary Key: UUID string provided by client is preferred for session tracking.
    id = Column(String, primary_key=True, index=True) 
    
    # Timestamp: Useful for sorting sessions or cleaning up old ones.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Summary: Stores the LLM-generated summary of the conversation so far.
    # Why: This is crucial for "Infinite Memory". Instead of feeding all 100+ messages,
    # we feed this summary + last N messages to the LLM.
    summary = Column(Text, nullable=True)
    
    # Relationships: Cascade delete ensures data cleanup when a session is deleted.
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    """
    Stores individual chat messages (User and Assistant).
    
    Why this table exists:
    ----------------------
    - To maintain the history of the conversation for display and context.
    - Historical messages are retrieved to provide immediate context to the LLM.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key: Links message to a specific session.
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    
    # Role: 'user' or 'assistant'. standardizes who said what.
    role = Column(String) 
    
    # Content: The actual text of the message.
    content = Column(Text)
    
    # Created At: Critical for ordering messages chronologically.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="messages")
    
    # Composite Index:
    # Why: We frequently query messages BY session_id AND sorted BY created_at.
    # A composite index optimizes this specific query pattern (SELECT ... WHERE session_id = ? ORDER BY created_at DESC).
    __table_args__ = (
        Index('idx_messages_session_time', 'session_id', 'created_at'),
    )

class Document(Base):
    """
    Stores metadata for file uploads (PDFs, Text files).
    
    Why this table exists:
    ----------------------
    - To track which files were uploaded to which session.
    - Stores the full extracted content as a backup/reference, even though usage 
      relies mainly on the chunks.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    
    filename = Column(String)
    
    # Content: The raw text extracted from the file.
    # Why: Useful if we ever need to re-chunk with different parameters without re-uploading.
    content = Column(Text) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("Session", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    """
    Stores small chunks of text and their vector embeddings.
    
    Why this table exists:
    ----------------------
    - RAG (Retrieval Augmented Generation) works by finding small, relevant pieces of text.
    - Storing whole documents is inefficient for semantic search.
    - Chunks are embedded into vectors using an Embedding Model.
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Linking chunk back to the source document.
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # The actual text snippet provided to the LLM as context.
    content = Column(Text)
    
    # Vector Embedding:
    # Uses pgvector's Vector type.
    # Dimension is dynamic based on provider (OpenAI=1536, Gemini=768).
    # Why: This is the core of semantic search. We compare the user query vector 
    # to these vectors to find similarity.
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION)) 

    document = relationship("Document", back_populates="chunks")

    # Note on Indexes for Vector Search:
    # For production with millions of rows, we would add an HNSW index here:
    # Index('idx_embedding', embedding, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64})
    # However, creating HNSW indexes via SQLAlchemy in `create_all` can be complex without raw SQL 
    # and requires data to be efficient. For this assignment, the table definition is sufficient.
