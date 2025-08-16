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

# DEBUG: Show what we copied - step by step
RUN echo "=== DEBUG: Files copied ==="
RUN ls -la src/ || echo "src/ directory missing!"
RUN ls -la src/tcg_research/ || echo "tcg_research/ directory missing!"
RUN ls -la src/tcg_research/models/ || echo "models/ directory missing!"
RUN test -f src/tcg_research/models/__init__.py && echo "models/__init__.py exists" || echo "models/__init__.py MISSING!"
RUN test -f src/tcg_research/models/database.py && echo "database.py exists" || echo "database.py MISSING!"

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Use app-dir to point to src layout
CMD ["uvicorn", "tcg_research.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]