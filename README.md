# AI Chatbot with RAG

This is a backend API for an AI Chatbot that supports Retrieval Augmented Generation (RAG) and session management. It uses an optimized database schema for performance.

## Features

- **Chat Interface**: Interact with an AI agent.
- **RAG (Retrieval Augmented Generation)**: Upload documents to ground the AI's responses.
- **Optimized History**: Retains full history in DB but only feeds relevant recent messages + summary to the LLM.
- **Conversation Summarization**: Automatically maintains a running summary of the conversation in the background.
- **Session Management**: Conversation history and uploaded documents are isolated by `session_id`.
- **Persistent Storage**: All data (chats, files, embeddings) is stored in PostgreSQL.
- **Vector Search**: Uses `pgvector` for efficient similarity search.

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with `pgvector` extension
- **ORM**: SQLAlchemy (Async) + asyncpg
- **LLM Orchestration**: LangChain
- **Containerization**: Docker & Docker Compose

## Prerequisites

- **Docker** and **Docker Compose** installed on your machine.
- An **OpenAI API Key** (or compatible LLM provider key).

## Setup and Execution

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Environment Configuration**:
   Copy the example environment file and configure your API key.
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set your `OPENAI_API_KEY`.
   ```ini
   OPENAI_API_KEY=sk-...
   ```
   You can leave the# Atlantis AI Chatbot Backend

## 1. Overview
This project is a production-ready AI Chatbot Backend designed to be **LLM-Agnostic** (supporting both OpenAI and Google Gemini). It features **Retrieval Augmented Generation (RAG)**, **Session Management**, **Long-term Memory (Summarization)**, and **Vector Search** using PostgreSQL + pgvector.

---

## 🏗️ Reviewer Guide / Quick Start
*Steps for the evaluation team to run and test the project.*

### Step 1: Clone & Configure
```bash
git clone <this-repo-url>
cd ATLANTIS
# Copy the example env file
cp .env.example .env
```
Inside `.env`, populate your **Google API Key**:
```ini
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
# Note: 'gemini-2.5-flash' is the recommended model for free tier efficiency.
```

### Step 2: Run with Docker (Recommended)
This command sets up the Database (Postgres + pgvector) and the Backend API automatically.
```bash
docker-compose up --build
```
> **Note on 429 Errors**: The application uses the Google Gemini Free Tier, which has strict rate limits (approx 15-20 requests/minute/day depending on the model). 
> The application includes **Automatic Retry Logic** (backoff) to handle `429 RESOURCE_EXHAUSTED` errors. If you see delays, please be patient as the system is retrying.

### Step 3: Test Functionality
**Method A: Swagger UI (Easiest)**
Navigate to: 👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

**Method B: PowerShell / Terminal**
1. **Upload Context** (Dummy file):
   ```powershell
   "This is a secret project." | Out-File secret.txt
   curl -X POST "http://localhost:8000/api/upload" -F "file=@secret.txt" -F "session_id=review-session"
   ```
2. **Chat (RAG Test)**:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Method POST -ContentType "application/json" -Body '{"query": "What is the secret project?", "session_id": "review-session"}'
   ```

---

## 🚀 Features & Bonus Points Implementation
This project meets all requirements and includes the following **Bonus Features**:

- ✅ **Descriptive Comments**: Every module, class, and critical function is documented with "Why" and "How" comments (see `app/services/chat_service.py`).
- ✅ **Architecture Diagram**: Included in `architecture.mmd` (root directory).
- ✅ **Docker Containerization**: Full `docker-compose.yml` setup for 1-command startup.
- ✅ **Session Management**: All chats and documents are isolated by `session_id`.
- ✅ **Retry Mechanism**: Robust handling of LLM Rate Limits (429).
- ✅ **Configurable LLM**: Seamless switch between `openai` and `gemini` via `.env`.

---

## 2. Architecture
The system is built using:
- **Backend Framework**: FastAPI (Async)
- **Database**: PostgreSQL 16
- **Vector Search**: pgvector extension
- **AI Framework**: LangChain
- **LLM Providers**: Google Gemini (Default) or OpenAI

## 3. Local Setup (Manual / Non-Docker)
If you cannot use Docker, follow these steps:

1. **Install PostgreSQL 16** and enable `pgvector` extension.
2. **Create Database**: `chatbot_db`
3. **Update .env**:
   ```ini
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_db
   ```
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Run Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## 4. Troubleshooting
- **429 RESOURCE_EXHAUSTED**: You hit the Google Free Tier quota. The app will auto-retry. If it persists, try switching to a paid key or OpenAI.
- **pgvector not found**: Ensure you are using the `pgvector/pgvector:pg16` Docker image (configured in docker-compose.yml).

   *Note: This might take a few minutes for the first build.*

4. **Verify Running**:
   Once started, the API will be accessible at:
   - **API Root**: `http://localhost:8000`
   - **Swagger Documentation**: `http://localhost:8000/docs`

## API Usage

You can use the Swagger UI (`/docs`) or tools like `curl` / Postman.

### 1. Upload a Document (Context)
Upload a file to a specific session.

**Endpoint**: `POST /api/upload`
**Form Data**:
- `file`: (File) The PDF or Text file.
- `session_id`: (String) Unique identifier for the session (e.g., "session-123").

```bash
curl -X 'POST' \
  'http://localhost:8000/api/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/document.pdf' \
  -F 'session_id=session-123'
```

### 2. Chat with the Bot
Send a message. If you uploaded documents to the same `session_id`, the bot will use them as context.

**Endpoint**: `POST /api/chat`
**JSON Body**:
```json
{
  "query": "What does the document say about X?",
  "session_id": "session-123"
}
```

## 7. Future Optimizations

- **Redis Caching**: Introduce Redis to cache frequent session summaries or recent messages for extremely high-throughput environments.
- **Asynchronous Processing Queue**: For very large file uploads, offload processing to a dedicated worker queue (e.g., Celery) to avoid holding HTTP connections.
