# Orange Code - AI Coding Assistant

A production-ready autonomous coding assistant with advanced scheduler functionality and tool management system.

## 🚀 Quick Start

```bash
# Install dependencies
pip install ollama rich requests pydantic

# Start Orange Code
python3 orangecode.py

# Or use test environment
cd tests && ./run.sh
```

## 🎯 Key Features

### Advanced Scheduler Architecture
- **Lazy Loading**: Fast CLI startup with deferred initialization
- **Concurrency Control**: Prevents API overload with semaphore limits
- **Streaming Display**: Real-time output with tool call synchronization
- **Project Context**: Automatic loading of project configuration

### Tool Management System
- **5 Core Tools**: File operations, shell commands, code analysis
- **Permission Levels**: 4 granular access control levels
- **Skill-Based Access**: Role-based tool filtering

### LLM Integration
- **Ollama Support**: Local LLM integration with qwen2.5-coder:3b
- **Retry Mechanism**: Intelligent error handling with exponential backoff
- **Rate Limiting**: Built-in request throttling

## 📋 Available Skills

Choose your expertise level:

1. **Developer** - Coding and development tasks
2. **Analyst** - Code analysis and review
3. **System** - System administration
4. **General** - General assistance

## 🛠️ Available Tools

- `read_file` - Read file contents
- `write_file` - Write content to files
- `execute_shell` - Execute shell commands
- `list_files` - List directory contents
- `safe_file_operations` - Secure file operations

## 🔧 Configuration

Set environment variables:

```bash
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="qwen2.5-coder:3b"
```

## 📁 Project Structure

```
Orange Code/
├── agent.py              # Main scheduler implementation
├── orangecode.py         # CLI entry point
├── tool_executor.py      # Tool execution engine
├── tools.py              # Tool definitions and permissions
├── retry.py             # LLM retry mechanism
├── utils.py              # Shared utilities
├── tests/                # Test environment
├── AGENTS.md             # Project context (for AI)
└── requirements.txt       # Python dependencies
```

## 📚 Documentation

- `AGENTS.md` - Project context for AI agent
- `requirements.txt` - Python dependencies
- This README provides all necessary usage information

## 🤝 Contributing

This is a production-ready AI coding assistant. Feel free to use and adapt for your needs.

## 📄 License

[Add your license here]

## 🎊 Status

✅ Production Ready - All core features implemented and tested