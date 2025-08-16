#!/usr/bin/env python3
"""Debug tool for Docker deployment issues."""

import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: str, capture: bool = True) -> tuple[int, str]:
    """Run command and return exit code and output."""
    try:
        result = subprocess.run(
            cmd, shell=True, text=True, 
            capture_output=capture, check=False
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def check_file_structure():
    """Check that all required files exist."""
    print("🔍 Checking file structure...")
    
    required_files = [
        "src/tcg_research/__init__.py",
        "src/tcg_research/api/__init__.py", 
        "src/tcg_research/core/__init__.py",
        "src/tcg_research/models/__init__.py",
        "src/tcg_research/models/database.py",
        "src/tcg_research/api/main.py",
        "pyproject.toml",
        "requirements.txt"
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            print(f"❌ MISSING: {file_path}")
        else:
            print(f"✅ Found: {file_path}")
    
    if missing:
        print(f"\n🚨 CRITICAL: {len(missing)} required files missing!")
        return False
    
    print("✅ All required files present")
    return True


def check_dockerignore():
    """Check .dockerignore for problematic patterns."""
    print("\n🔍 Checking .dockerignore...")
    
    dockerignore_path = Path(".dockerignore")
    if not dockerignore_path.exists():
        print("⚠️  No .dockerignore found")
        return True
    
    content = dockerignore_path.read_text()
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    problematic_patterns = [
        "src/", "src/**", 
        "models/", "**/models/**", "models/**",
        "tcg_research/", "**/tcg_research/**"
    ]
    
    issues = []
    for line in lines:
        if line in problematic_patterns and not line.startswith('!'):
            issues.append(line)
            print(f"🚨 PROBLEMATIC: {line}")
    
    if issues:
        print(f"\n❌ Found {len(issues)} problematic .dockerignore patterns!")
        print("These patterns may exclude your source code from Docker build")
        return False
    
    print("✅ .dockerignore looks OK")
    return True


def test_imports():
    """Test if imports work locally."""
    print("\n🔍 Testing imports locally...")
    
    test_script = '''
import sys
sys.path.insert(0, "src")

try:
    from tcg_research.models.database import Card
    print("✅ Import tcg_research.models.database works")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

try:
    from tcg_research.core.features import FeatureEngineer  
    print("✅ Import tcg_research.core.features works")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

try:
    from tcg_research.api.main import app
    print("✅ Import tcg_research.api.main works")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
'''
    
    exit_code, output = run_cmd(f'python3 -c "{test_script}"')
    print(output)
    
    if exit_code == 0:
        print("✅ All imports work locally")
        return True
    else:
        print("❌ Import failures detected locally!")
        return False


def build_docker_locally():
    """Build Docker image locally to test."""
    print("\n🔍 Building Docker image locally...")
    
    exit_code, output = run_cmd("docker build -t tcg-test .", capture=True)
    print(output[-1000:])  # Last 1000 chars
    
    if exit_code == 0:
        print("✅ Docker build succeeded")
        return True
    else:
        print("❌ Docker build failed")
        return False


def test_docker_container():
    """Test running the container locally."""
    print("\n🔍 Testing Docker container...")
    
    # Try to run container and test import
    test_cmd = 'docker run --rm tcg-test python -c "from tcg_research.models.database import Card; print(\\"Import works in container\\")"'
    
    exit_code, output = run_cmd(test_cmd)
    print(output)
    
    if exit_code == 0:
        print("✅ Container imports work")
        return True
    else:
        print("❌ Container import failed")
        return False


def show_file_tree():
    """Show the actual file tree."""
    print("\n📁 File tree:")
    exit_code, output = run_cmd("find src -name '*.py' | head -20")
    print(output)


def main():
    """Run all debugging checks."""
    print("🚀 TCG Research Docker Debug Tool")
    print("=" * 50)
    
    checks = [
        ("File Structure", check_file_structure),
        ("Dockerignore", check_dockerignore), 
        ("Local Imports", test_imports),
        ("Docker Build", build_docker_locally),
        ("Container Test", test_docker_container),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results[name] = False
    
    show_file_tree()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Deploy should work.")
        return 0
    else:
        print(f"\n🚨 {sum(1 for x in results.values() if not x)} checks failed!")
        print("Fix the failing checks before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())