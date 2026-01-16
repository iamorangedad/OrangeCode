# AI Agent Configuration

## Project Overview
This is the Orange Code project - an autonomous AI coding assistant with RAG and no-RAG variants.

## Technology Stack
- **Python 3.11** - Primary programming language
- **Ollama** - LLM inference with qwen2.5-coder:3b model
- **Rich** - Terminal UI and formatting
- **ChromaDB** - Vector database (RAG variant only)
- **FastAPI** - API framework (RAG variant only)
- **Kubernetes** - Deployment platform

## Code Standards
- Use Python type hints where possible
- Follow PEP 8 style guidelines
- Document functions with docstrings
- Use rich console for all user output
- Handle exceptions gracefully

## Common Commands
- **Development**: `cd test-no-rag && ./run.sh`
- **Testing**: `uv run python test_environment.py`
- **Deployment**: `kubectl apply -k deploy/deploy-no-rag/`
- **Dependencies**: `uv add package-name`

## Project Structure
```
agent_no_rag.py          # Main no-RAG agent with scheduler
agent_with_rag.py        # RAG-enhanced agent
agent.py                 # Base agent implementation
utils.py                 # Shared utilities
test-no-rag/             # Local testing environment
deploy/deploy-no-rag/     # Kubernetes deployment
rag/                     # RAG service components
```

## Agent Behavior Guidelines
- Always use tools for file operations
- Ask for confirmation before running shell commands
- Provide step-by-step reasoning
- Format responses in JSON when using tools
- Use streaming output for better UX

## Current Working Directory Context
The agent operates in the project root directory and has access to all source files.