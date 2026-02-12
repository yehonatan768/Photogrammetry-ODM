FROM python:3.11-slim

WORKDIR /app

# System deps: ffmpeg for frame extraction; curl for debugging; build deps for some wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY docker/pipeline/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy is optional because we mount the project, but useful for CI builds
COPY . /app

CMD ["python", "-m", "src.cli", "--help"]
