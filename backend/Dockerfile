# ─── Backend Dockerfile ───────────────────────────────────────────────────────
# Python 3.11-slim — matches installed local Python version
FROM python:3.11-slim

# Prevents .pyc files and enables unbuffered stdout for clean logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed for cryptography / pymongo
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Expose FastAPI port
EXPOSE 8000

# Run with Uvicorn — entrypoint is app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
