from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
import logging

# Configure logger
logger = logging.getLogger(__name__)

def get_embeddings_service():
    """
    Factory function to return the configured Embeddings Service.
    
    Why:
    ----
    - The application needs to be configurable to switch between LLM providers (OpenAI, Gemini).
    - Different providers use different embedding models with different dimensions.
    - Centralizing this logic allows easily swapping the provider in .env without changing code.
    
    Logic:
    ------
    - Checks `settings.LLM_PROVIDER` (loaded from environment).
    - If 'gemini', returns `GoogleGenerativeAIEmbeddings` using `text-embedding-004`.
    - If 'openai', returns `OpenAIEmbeddings` using `text-embedding-3-small` (default).
    
    Returns:
    --------
    Embeddings: A LangChain Embeddings interface compatible object.
    """
    provider = settings.LLM_PROVIDER
    
    try:
        if provider == "gemini":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is missing in configuration.")
            
            # Gemini Embeddings
            # Model: text-embedding-004 is the latest stable model
            # Dimension: 768
            logger.info("Initializing Google Gemini Embeddings (text-embedding-004)")
            return GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=settings.GOOGLE_API_KEY,
                task_type="retrieval_document" # optimizing for retrieval
            )
            
        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is missing in configuration.")
                
            # OpenAI Embeddings
            # Model: text-embedding-3-small is cost-effective and performant
            # Dimension: 1536
            logger.info("Initializing OpenAI Embeddings (text-embedding-3-small)")
            return OpenAIEmbeddings(
                model="text-embedding-3-small", 
                api_key=settings.OPENAI_API_KEY
            )
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
            
    except Exception as e:
        logger.error(f"Failed to initialize embeddings service: {e}")
        raise e
