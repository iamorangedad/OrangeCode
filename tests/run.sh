#!/bin/bash
# Run script for no-RAG agent

# Load environment variables (skip comments)
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "🌍 Loaded environment from .env"
fi

echo "🚀 Starting Orange Code Agent..."
echo "📍 Ollama Host: ${OLLAMA_HOST:-http://10.0.0.55:11434}"
echo "💬 To quit: type 'quit' or 'exit'"
echo ""

# Run the agent
cd .. && uv run --script orangecode.py