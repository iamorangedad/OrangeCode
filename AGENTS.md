# AI Agent Configuration

## Project Overview
This is the Orange Code project - an autonomous AI coding assistant with advanced scheduler functionality.

## Technology Stack
- **Python 3.11** - Primary programming language
- **Ollama** - LLM inference with qwen2.5-coder:3b model
- **Rich** - Terminal UI and formatting
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
utils.py                 # Shared utilities
cli.py                   # CLI entry point
tests/                    # Local testing environment
deploy/                   # Kubernetes deployment
```

## Agent Behavior Guidelines
- Always use tools for file operations
- Ask for confirmation before running shell commands
- Provide step-by-step reasoning
- Format responses in JSON when using tools
- Use streaming output for better UX

## Current Working Directory Context
The agent operates in the project root directory and has access to all source files.