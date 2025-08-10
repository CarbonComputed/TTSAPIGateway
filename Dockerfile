# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies required for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    libasound2 \
    libasound2-dev \
    libportaudio2 \
    libportaudio-dev \
    libavcodec-extra \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies and spaCy model
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Copy application code
COPY app.py .

# Expose port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5050/health || exit 1

# Run the application
CMD ["python", "app.py"] 