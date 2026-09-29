#!/usr/bin/env python3
"""
Setup script for no-RAG agent with uv environment
"""

import os
import subprocess
from pathlib import Path


def setup_environment():
    """Setup the testing environment"""
    print("🚀 Setting up no-RAG Agent Environment")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ This script must be run from the test-no-rag directory")
        return False

    # Configure environment variables
    print("\n🔧 Environment Configuration:")

    # Ollama host configuration
    ollama_host = input("Enter Ollama host (default: http://10.0.0.55:11434): ").strip()
    if not ollama_host:
        ollama_host = "http://10.0.0.55:11434"

    # Create .env file
    env_content = f"""# Environment configuration for no-RAG agent
OLLAMA_HOST={ollama_host}
PYTHONUNBUFFERED=1
"""

    with open(".env", "w") as f:
        f.write(env_content)

    print(f"✅ .env file created with OLLAMA_HOST={ollama_host}")

    # Install dependencies
    print("\n📦 Installing dependencies with uv...")
    result = subprocess.run(
        ["uv", "add", "requests"], capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Dependencies installed successfully")
    else:
        print(f"❌ Failed to install dependencies: {result.stderr}")
        return False

    return True


def create_run_script():
    """Create a convenient run script"""
    run_script = """#!/bin/bash
# Start Orange Code from the tests directory.

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "Starting Orange Code"
cd .. && python3 orangecode.py
"""

    with open("run.sh", "w") as f:
        f.write(run_script)

    # Make it executable
    os.chmod("run.sh", 0o755)
    print("✅ run.sh script created")


def main():
    if setup_environment():
        create_run_script()

        print("\n" + "=" * 40)
        print("🎉 Environment setup complete!")
        print("\n📝 Next steps:")
        print("1. Ensure Ollama is running at your specified host")
        print("2. Run the agent with: ./run.sh")
        print("3. Or run manually: python3 ../orangecode.py")
        print("\n🧪 Test the environment:")
        print("   uv run python test_environment.py")
    else:
        print("❌ Setup failed!")


if __name__ == "__main__":
    main()
