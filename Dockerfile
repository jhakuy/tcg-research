FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code directly to app root - flatten the structure
COPY src/tcg_research/ ./tcg_research/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY init-db.sql .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run uvicorn - now tcg_research is directly in /app
CMD ["python", "-m", "uvicorn", "tcg_research.api.main:app", "--host", "0.0.0.0", "--port", "8000"]