FROM python:3.12-slim

# Install ffmpeg for yt-dlp audio extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY openclaw/ ./openclaw/
COPY pipelines/ ./pipelines/
COPY utils/ ./utils/
COPY doctrine/ ./doctrine/
COPY schemas/ ./schemas/
COPY run_daily.py .

# Create working directories
RUN mkdir -p /app/downloads /app/data /app/ncl_out /app/.tmp

# Set environment defaults
ENV DOWNLOAD_DIR=/app/downloads
ENV DATABASE_URL=sqlite:///./youtubedrop.db
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "openclaw"]
