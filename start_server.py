#!/usr/bin/env python3
"""Direct Python startup script that ensures imports work."""

import os
import sys

# Add src to path if needed
src_path = '/app/src'
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)

# Verify imports
try:
    print(f"Python path: {sys.path[:3]}")
    import tcg_research.models.database
    print("✓ Imports verified successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Start uvicorn
import uvicorn
uvicorn.run("tcg_research.api.main:app", host="0.0.0.0", port=8000)