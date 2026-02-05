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
   You can leave the Database settings as default if running via Docker.

3. **Start the Application**:
   Run the following command to build and start the backend and database containers.
   ```bash
   docker-compose up --build
   ```
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

## Architecture

The application follows a layered architecture (Service-Repository pattern).

```mermaid
graph TD
    User[User/Client] -->|JSON Request| API[FastAPI Backend]
    
    subgraph "Application Layer"
        API -->|/chat| ChatService[Chat Service]
        API -->|/upload| FileService[File Service]
        ChatService -->|Background Task| SummaryService[Summary Updater]
    end
    
    subgraph "Data Layer"
        ChatService -->|Store History| Messages[Message Table]
        Messages -->|Indexed Access| ChatService
        SummaryService -->|Update Summary| SessionTbl[Session Table]
        FileService -->|Store Metadata| Documents[Document Table]
        FileService -->|Store Embeddings| VectorStore[DocumentChunk Table]
        ChatService -->|Vector Search| VectorStore
    end
    
    subgraph "External Services"
        ChatService -->|Completion| LLM[LLM (OpenAI)]
        SummaryService -->|Summarization| LLM
        FileService -->|Embeddings| LLM
    end
```

## Future Optimizations

- **Redis Caching**: Introduce Redis to cache frequent session summaries or recent messages for extremely high-throughput environments.
- **Asynchronous Processing Queue**: For very large file uploads, offload processing to a dedicated worker queue (e.g., Celery) to avoid holding HTTP connections.

## Troubleshooting

- **Database Connection Error**: Ensure the `db` container is healthy. The backend waits for it, but if it fails, check `docker-compose logs db`.
- **OpenAI Error**: Ensure your API key is correct in `.env`.
