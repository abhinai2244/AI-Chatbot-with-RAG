import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/chatbot_db")
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower() # Options: openai, gemini
    
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Gemini Settings
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Embedding Dimensions
    # Gemini (text-embedding-004) = 768
    # OpenAI (text-embedding-3-small) = 1536
    EMBEDDING_DIMENSION = 768 if LLM_PROVIDER == "gemini" else 1536
    
settings = Settings()
