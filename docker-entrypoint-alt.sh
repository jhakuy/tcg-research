#!/bin/bash
set -e

echo "Starting TCG Research API (Alternative Setup)..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "PYTHONPATH: $PYTHONPATH"
echo "Contents of /app:"
ls -la /app/

# Verify imports work
python -c "
import sys
print('Python path:', sys.path[:3])
try:
    import tcg_research.models.database
    print('✓ Import verification successful')
except ImportError as e:
    print(f'✗ Import failed: {e}')
    print('Looking for tcg_research in:', sys.path)
    import os
    if os.path.exists('/app/tcg_research'):
        print('/app/tcg_research exists')
        if os.path.exists('/app/tcg_research/models'):
            print('/app/tcg_research/models exists')
    sys.exit(1)
"

# Start the application
exec python -m uvicorn tcg_research.api.main:app --host 0.0.0.0 --port 8000