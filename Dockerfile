# ------------------------------------------------------------------------------
# Dockerfile for Atlantis Backend
# ------------------------------------------------------------------------------

# 1. Base Image: Python 3.11 Slim (Minimal size)
FROM python:3.11-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Install System Dependencies
# libpq-dev is required for psycopg2/asyncpg to build
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Application Code
COPY . .

# 6. Expose Port 8000 (FastAPI default)
EXPOSE 8000

# 7. Start Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
