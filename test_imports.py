#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

import sys
import os

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"Python path: {sys.path[:3]}")

try:
    import tcg_research
    print("✓ tcg_research imported")
    
    import tcg_research.models
    print("✓ tcg_research.models imported")
    
    import tcg_research.models.database
    print("✓ tcg_research.models.database imported")
    
    import tcg_research.api.main
    print("✓ tcg_research.api.main imported")
    
    import tcg_research.core.features
    print("✓ tcg_research.core.features imported")
    
    print("\n✅ All imports successful! The module structure is correct.")
    
except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    print("\nDebug info:")
    print(f"Looking for tcg_research in: {sys.path[0] if sys.path else 'No path set'}")
    
    # Check if directories exist
    if os.path.exists('/app/src/tcg_research'):
        print("✓ /app/src/tcg_research exists")
        if os.path.exists('/app/src/tcg_research/models'):
            print("✓ /app/src/tcg_research/models exists")
            if os.path.exists('/app/src/tcg_research/models/database.py'):
                print("✓ /app/src/tcg_research/models/database.py exists")
    else:
        print("✗ /app/src/tcg_research does not exist")