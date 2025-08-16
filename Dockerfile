FROM python:3.10-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code explicitly
COPY src/ /app/src/
COPY start_server.py /app/
COPY requirements.txt /app/
# Copy other project files if they exist
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Set PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Verify the structure is correct
RUN ls -la /app/ && \
    ls -la /app/src/ && \
    ls -la /app/src/tcg_research/ && \
    ls -la /app/src/tcg_research/models/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Stay in /app directory
WORKDIR /app

# Run using the startup script that handles imports correctly
CMD ["python", "/app/start_server.py"]