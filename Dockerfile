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

# Copy source code and package configuration
COPY src/ ./src/
COPY pyproject.toml .
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY init-db.sql .

# Install the package in editable mode - this fixes the import issue
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run uvicorn - now tcg_research is properly installed as a package
CMD ["uvicorn", "tcg_research.api.main:app", "--host", "0.0.0.0", "--port", "8000"]