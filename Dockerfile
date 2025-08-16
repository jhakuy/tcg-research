FROM python:3.10-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# If you need psycopg2/scipy to compile
RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

# 1) Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy the repo (your .dockerignore will keep junk out)
COPY . .

# 3) Normalize: ensure /app/src points to your actual src tree
#    Works for either layout: "src/..." or "TCG_RESEARCH/src/..."
RUN set -eux; \
    if [ -d "/app/src/tcg_research" ]; then \
        echo "Using /app/src"; \
    elif [ -d "/app/TCG_RESEARCH/src/tcg_research" ]; then \
        echo "Using /app/TCG_RESEARCH/src -> symlink to /app/src"; \
        ln -s /app/TCG_RESEARCH/src /app/src; \
    else \
        echo "ERROR: Could not find tcg_research under /app/src or /app/TCG_RESEARCH/src"; \
        ls -la /app || true; \
        ls -la /app/TCG_RESEARCH || true; \
        exit 1; \
    fi

# 4) Make /app/src importable and HARD sanity check
ENV PYTHONPATH=/app/src
RUN echo "== Listing /app/src/tcg_research ==" && ls -la /app/src/tcg_research || true
RUN echo "== Listing /app/src/tcg_research/models ==" && ls -la /app/src/tcg_research/models || true
RUN cd /app/src && python -c "import tcg_research.models.database; print('Import OK: tcg_research.models.database')"

# 5) Non-root (optional)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 6) Start the app from the src layout
CMD ["uvicorn", "tcg_research.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]