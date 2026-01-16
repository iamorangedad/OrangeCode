#!/bin/bash
# Run script for no-RAG agent

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "🌍 Loaded environment from .env"
fi

echo "🚀 Starting no-RAG Agent..."
echo "📍 Ollama Host: ${OLLAMA_HOST:-http://10.0.0.55:11434}"
echo "💬 To quit: type 'quit' or 'exit'"
echo ""

# Run the agent
uv run python agent_no_rag.py