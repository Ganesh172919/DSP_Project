FROM python:3.11-slim

WORKDIR /app

# System dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY training/ training/

# Create data directories
RUN mkdir -p data weights keys

# Download InsightFace model weights on build
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l')" || true

# Environment variables
ENV FACE_AUTH_AES_KEY="0000000000000000000000000000000000000000000000000000000000000000"
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
