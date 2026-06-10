FROM python:3.11-slim

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source code (from root context)
COPY . .
ENV PYTHONPATH=/app

# Commands for backend and workers are overridden by docker-compose.yml
