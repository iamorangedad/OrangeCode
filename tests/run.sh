#!/bin/bash
# Start Orange Code from the repository root.

# Load environment variables (skip comments)
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "🌍 Loaded environment from .env"
fi

echo "Starting Orange Code"
echo "Base URL: ${BASE_URL:-${OLLAMA_HOST:-http://127.0.0.1:11434}}"
echo "Model: ${MODEL:-${OLLAMA_MODEL:-qwen2.5-coder:3b}}"
echo ""

cd .. && python3 orangecode.py