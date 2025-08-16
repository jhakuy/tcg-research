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

# Copy source code and entry point
COPY src/ ./src/
COPY main.py .
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY init-db.sql .

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application via main.py
CMD ["python", "main.py"]