FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the tcg_research package directly to /app
COPY src/tcg_research /app/tcg_research

# Copy other necessary files
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Create a simple startup script
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import sys\n\
print("="*50)\n\
print("TCG Research API - Startup Diagnostics")\n\
print("="*50)\n\
print(f"Working directory: {os.getcwd()}")\n\
print(f"Python path: {sys.path[:3]}")\n\
db_set = "DATABASE_URL" in os.environ\n\
print(f"DATABASE_URL set: {db_set}")\n\
port_val = os.environ.get("PORT", "8000 (default)")\n\
print(f"PORT: {port_val}")\n\
app_contents = os.listdir("/app")\n\
print(f"Contents of /app: {app_contents}")\n\
if os.path.exists("/app/tcg_research"):\n\
    tcg_contents = os.listdir("/app/tcg_research")\n\
    print(f"Contents of /app/tcg_research: {tcg_contents}")\n\
    if os.path.exists("/app/tcg_research/models"):\n\
        models_contents = os.listdir("/app/tcg_research/models")\n\
        print(f"Contents of /app/tcg_research/models: {models_contents}")\n\
        print("✓ Models directory found!")\n\
    else:\n\
        print("✗ Models directory NOT found!")\n\
else:\n\
    print("✗ tcg_research package NOT found!")\n\
print("="*50)\n\
print("Starting server...")\n\
try:\n\
    import tcg_research.api.main\n\
    print("✓ Successfully imported tcg_research.api.main")\n\
except ImportError as e:\n\
    print(f"✗ Failed to import: {e}")\n\
    sys.exit(1)\n\
import uvicorn\n\
port = int(os.environ.get("PORT", 8000))\n\
print(f"Starting server on port {port}")\n\
uvicorn.run("tcg_research.api.main:app", host="0.0.0.0", port=port)\n' > /app/start.py

# Make it executable
RUN chmod +x /app/start.py

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "/app/start.py"]