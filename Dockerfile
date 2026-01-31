# CodePilot Docker Image
# Multi-stage build for optimized production deployment

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Stage 2: Dependencies
FROM base AS dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies AS application

# Copy application code
COPY inference/ ./inference/
COPY model/ ./model/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Create directories for models and logs
RUN mkdir -p /app/model/checkpoints /app/logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["python3", "inference/server.py"]

# Default command
CMD ["--host", "0.0.0.0", "--port", "8000"]

# Stage 4: Development (optional)
FROM application AS development

# Install development tools
RUN pip3 install --no-cache-dir \
    pytest \
    black \
    flake8 \
    mypy \
    ipython

# Development entrypoint
CMD ["bash"]
