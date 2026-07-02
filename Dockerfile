# WOS-M Dockerfile
# © MANSOUR — WOS-M. All rights reserved.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/logs /app/data/backups

# Healthcheck using static system check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python main.py --check || exit 1

# Set entrypoint
ENTRYPOINT ["python", "main.py"]
