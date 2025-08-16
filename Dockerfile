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

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY init-db.sql .

# DEBUG: Show what we copied
RUN echo "=== DEBUG: Files copied ===" && \
    ls -la src/ && \
    echo "=== tcg_research contents ===" && \
    ls -la src/tcg_research/ && \
    echo "=== models contents ===" && \
    ls -la src/tcg_research/models/ && \
    echo "=== Test import ===" && \
    cd src && python -c "from tcg_research.models.database import Card; print('SUCCESS: Import works')"

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Use app-dir to point to src layout
CMD ["uvicorn", "tcg_research.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]