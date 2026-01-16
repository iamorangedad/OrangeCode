#!/usr/bin/env python3
"""
Test script for no-RAG agent with uv environment
"""

import os
import subprocess
import sys
from pathlib import Path


def test_dependencies():
    """Test that all required packages are installed"""
    try:
        import ollama
        import rich
        import requests

        print("✅ All dependencies installed successfully")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False


def test_ollama_connection():
    """Test connection to Ollama service"""
    try:
        import ollama

        ollama_host = os.getenv("OLLAMA_HOST", "http://10.0.0.55:11434")
        client = ollama.Client(host=ollama_host)
        models = client.list()
        print(f"✅ Connected to Ollama at {ollama_host}")
        print(f"📋 Available models: {[m['model'] for m in models.get('models', [])]}")
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False


def test_agent_files():
    """Test that agent files exist and are readable"""
    required_files = ["../agent_no_rag.py", "utils.py"]
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} found")
        else:
            print(f"❌ {file} missing")
            return False
    return True


def main():
    print("🧪 Testing no-RAG Agent Environment")
    print("=" * 40)

    tests = [
        ("Dependencies", test_dependencies),
        ("Agent Files", test_agent_files),
        ("Ollama Connection", test_ollama_connection),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n🔍 Testing {name}...")
        results.append(test_func())

    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Environment is ready.")
        print("\n🚀 To start the agent, run:")
        print("   uv run python ../agent_no_rag.py")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
