from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    session_id: str 

class ChatResponse(BaseModel):
    response: str
    session_id: str

class UploadResponse(BaseModel):
    filename: str
    session_id: str
    message: str
