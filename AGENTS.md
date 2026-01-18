# AI Agent Configuration

## Project Overview
This is the Orange Code project - an autonomous AI coding assistant with advanced scheduler functionality.

## Technology Stack
- **Python 3.11** - Primary programming language
- **Ollama** - LLM inference with qwen2.5-coder:3b model
- **Rich** - Terminal UI and formatting

## Code Standards
- Use Python type hints where possible
- Follow PEP 8 style guidelines
- Document functions with docstrings
- Use rich console for all user output
- Handle exceptions gracefully

## Common Commands
- **Development**: `cd tests && ./run.sh`
- **Direct Usage**: `python3 orangecode.py`
- **Dependencies**: `pip install package-name`

## Project Structure
```
agent.py              # Main scheduler with OrangeCodeScheduler
orangecode.py         # CLI entry point
tool_executor.py      # Tool execution engine
tools.py              # Tool definitions and permissions
retry.py             # LLM retry mechanism
utils.py              # Shared utilities
tests/                # Test environment
AGENTS.md             # This file - project context
```

## Agent Behavior Guidelines
- Always use tools for file operations
- Ask for confirmation before running shell commands
- Provide step-by-step reasoning
- Format responses in JSON when using tools
- Use streaming output for better UX

## Current Working Directory Context
The agent operates in the project root directory and has access to all source files.

## Available Skills
- **General**: General assistance
- **Developer**: Coding and development tasks
- **Analyst**: Code analysis and review
- **System**: System administration

## Available Tools
- `read_file` - Read file contents
- `write_file` - Write content to files
- `execute_shell` - Execute shell commands
- `list_files` - List directory contents
- `safe_file_operations` - Secure file operations

## LLM Configuration
- **Model**: qwen2.5-coder:3b
- **Host**: Configurable via OLLAMA_HOST environment variable
- **Retry**: Intelligent error handling with exponential backoff