#!/usr/bin/env python3
"""Direct Python startup script that ensures imports work."""

import os
import sys

# Debug: Show what's in the container
print("=== Docker Container Debug Info ===")
print(f"Current directory: {os.getcwd()}")
print(f"Contents of /app:")
for item in os.listdir('/app'):
    print(f"  - {item}")

if os.path.exists('/app/src'):
    print(f"Contents of /app/src:")
    for item in os.listdir('/app/src'):
        print(f"  - {item}")
    
    if os.path.exists('/app/src/tcg_research'):
        print(f"Contents of /app/src/tcg_research:")
        for item in os.listdir('/app/src/tcg_research'):
            print(f"  - {item}")
            
        if os.path.exists('/app/src/tcg_research/models'):
            print(f"Contents of /app/src/tcg_research/models:")
            for item in os.listdir('/app/src/tcg_research/models'):
                print(f"  - {item}")
else:
    print("ERROR: /app/src does not exist!")

# Add src to path if needed
src_path = '/app/src'
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)

# Verify imports
try:
    print(f"Python path: {sys.path[:3]}")
    
    # Try to import step by step for better debugging
    import tcg_research
    print("✓ tcg_research module found")
    
    import tcg_research.models
    print("✓ tcg_research.models module found")
    
    import tcg_research.models.database
    print("✓ tcg_research.models.database module found")
    
    print("✓ All imports verified successfully!")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"sys.path: {sys.path}")
    
    # Additional debugging
    print("\nTrying to locate tcg_research module:")
    for path in sys.path:
        test_path = os.path.join(path, 'tcg_research')
        if os.path.exists(test_path):
            print(f"  Found tcg_research at: {test_path}")
            models_path = os.path.join(test_path, 'models')
            if os.path.exists(models_path):
                print(f"    models/ exists with contents: {os.listdir(models_path)}")
            else:
                print(f"    models/ does NOT exist")
    
    sys.exit(1)

# Start uvicorn
import uvicorn
uvicorn.run("tcg_research.api.main:app", host="0.0.0.0", port=8000)