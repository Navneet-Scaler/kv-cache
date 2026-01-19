# =============================================================================
# KV-Cache Dockerfile
# =============================================================================
# Simple Docker image for the KV-Cache server
#
# Build:  docker build -t kv-cache .
# Run:    docker run -p 7171:7171 kv-cache
# Test:   echo "PUT test hello" | nc localhost 7171
# =============================================================================

FROM python:3.11-slim

# Labels
LABEL maintainer="Student Name <student@example.com>"
LABEL description="KV-Cache: In-Memory Key-Value Store"
LABEL version="1.0.0"

# Install netcat for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

WORKDIR /app

# Copy application source code
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Set Python path to find our modules
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7171

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD echo "EXISTS healthcheck" | nc -w 2 localhost 7171 | grep -q "OK" || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    KV_CACHE_HOST=0.0.0.0 \
    KV_CACHE_PORT=7171 \
    KV_CACHE_MAX_KEYS=10000

# Start server
CMD ["python", "-m", "src.server"]