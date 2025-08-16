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

# Copy ALL files to app root - bypass any path issues
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Change to src directory where the package lives
WORKDIR /app/src

# Expose port
EXPOSE 8000

# Run uvicorn from src directory
CMD ["python", "-m", "uvicorn", "tcg_research.api.main:app", "--host", "0.0.0.0", "--port", "8000"]