# Orange Code - AI Coding Assistant

A production-ready autonomous coding assistant with advanced scheduler functionality, tool management, and LLM API retry mechanisms.

## 🚀 Key Features

### 🎯 Advanced Scheduler Architecture
- **Lazy Loading**: Fast CLI startup with deferred initialization
- **Concurrency Control**: Prevents API overload with semaphore limits
- **Streaming Display**: Real-time output with tool call synchronization
- **ESC Cancellation**: Immediate interrupt via non-blocking keyboard detection
- **Project Context**: Automatic loading of project configuration from AGENTS.md

### 🛠️ Tool Management System
- **Decorator-Based Registration**: Simple `@function_tool` decorator for tool registration
- **Permission Levels**: 6 granular access control levels
- **Skill Restrictions**: Role-based tool access control
- **Permission Guard**: Automatic security checking for tool usage
- **Dynamic Filtering**: Runtime tool filtering based on active skills

### 🔄 Intelligent LLM Retry Mechanism
- **Exponential Backoff**: `delay * base^retry_count`
- **Random Jitter**: Prevents thundering herd with `delay * random()`
- **Error Classification**: 7 types of LLM API errors
- **Configurable Parameters**: Flexible retry configuration
- **Rich Logging**: Detailed retry statistics and progress tracking

### 🎮 User Experience
- **Rich Terminal UI**: Beautiful formatting with live updates
- **Progress Tracking**: Visual feedback on retry attempts and success rates
- **Error Handling**: Clear error messages with suggestions

## 🚀 Deployment Options

### Local Development (Recommended)
```bash
# Install as system command
pip install -e .

# Use directly
orangecode "your query here"
```

### Testing Environment
```bash
cd tests
uv run python ../agent.py
```

## 📁 Project Structure

```
📁 Orange Code/
├── 🤖 agent.py              # Main AI agent with scheduler
├── 🛠️ utils.py              # Shared utility functions  
├── 🔄 retry.py             # LLM retry mechanism
├── 🧪 tool_executor.py      # Enhanced tool execution
├── 🎯 cli.py                # CLI entry point (`orangecode`)
├── 🧪 tests/                # Local testing environment with uv
├── 📋 AGENTS.md              # Project context configuration
├── 📚 requirements.txt           # Dependencies
└── 📖 documentation/           # Comprehensive guides

## 🎯 Quick Start

```bash
# Install
pip install -e .

# Use immediately
orangecode "write a python function for fibonacci"

# Show configuration
orangecode config

# Interactive mode
orangecode
```

## 🌟 Benefits

- **Production Ready**: Enterprise-grade error handling and reliability
- **Developer Friendly**: Simple CLI with rich documentation
- **High Performance**: Optimized for local execution
- **Maintainable**: Clean, focused codebase
- **Secure**: Permission-based tool access control