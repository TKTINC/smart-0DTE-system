# Multi-stage build for lean deployment
FROM python:3.11-slim as builder

# Set build arguments
ARG ENVIRONMENT=lean-production

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.lean.txt /tmp/requirements.txt

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables for lean deployment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=lean-production \
    LEAN_MODE=true \
    DATA_OPTIMIZATION_ENABLED=true \
    CACHE_OPTIMIZATION_ENABLED=true \
    AI_OPTIMIZATION_ENABLED=true

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r smart0dte && useradd -r -g smart0dte smart0dte

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=smart0dte:smart0dte . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/models /app/cache && \
    chown -R smart0dte:smart0dte /app

# Switch to non-root user
USER smart0dte

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command with lean configuration
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-log", \
     "--log-level", "info", \
     "--no-server-header"]

