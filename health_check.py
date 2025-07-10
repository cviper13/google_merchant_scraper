#!/usr/bin/env python3
"""
Health check script for the scraper container
"""
import sys
import os
import requests
from pathlib import Path

def check_dependencies():
    """Check if required Python packages are importable"""
    try:
        import requests
        import bs4
        import paramiko
        return True
    except ImportError as e:
        print(f"Dependency check failed: {e}")
        return False

def check_data_directory():
    """Check if data directory exists and is writable"""
    data_dir = Path(".data")
    try:
        data_dir.mkdir(exist_ok=True)
        test_file = data_dir / "health_check.tmp"
        test_file.write_text("test")
        test_file.unlink()
        return True
    except Exception as e:
        print(f"Data directory check failed: {e}")
        return False

def check_network():
    """Check if network connectivity is available"""
    try:
        response = requests.get("https://www.utkuoptik.com", timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Network check failed: {e}")
        return False

def main():
    """Run all health checks"""
    checks = [
        ("Dependencies", check_dependencies),
        ("Data Directory", check_data_directory),
        ("Network", check_network)
    ]
    
    all_passed = True
    for name, check_func in checks:
        if check_func():
            print(f"✅ {name}: OK")
        else:
            print(f"❌ {name}: FAILED")
            all_passed = False
    
    if all_passed:
        print("🎉 All health checks passed!")
        sys.exit(0)
    else:
        print("💥 Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
