# Production Dockerfile for DocXtract Backend
FROM python:3.11-slim

# Install system dependencies for OpenCV and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-deva \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
