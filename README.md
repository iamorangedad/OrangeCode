# Orange Code - AI Coding Assistant

A production-ready autonomous coding assistant with advanced scheduler functionality and tool management system.

## 🚀 Quick Start

```bash
# Install as system command
pip install -e .

# Use immediately
orangecode "write a python function for fibonacci"

# Show configuration  
orangecode config

# Interactive mode
orangecode
```

## 🚀 Key Features

### 🎯 Advanced Scheduler Architecture
- **Lazy Loading**: Fast CLI startup with deferred initialization
- **Concurrency Control**: Prevents API overload with semaphore limits
- **Streaming Display**: Real-time output with tool call synchronization
- **ESC Cancellation**: Immediate interrupt via keyboard detection
- **Project Context**: Automatic loading of project context

### 🛠️ Tool Management System
- **Decorator-Based Registration**: Simple `@function_tool` decorator
- **Permission Levels**: 6 granular access control levels
- **Skill Restrictions**: Role-based tool access control
- **Dynamic Filtering**: Runtime tool filtering based on active skills

### 🔄 Intelligent LLM Retry Mechanism
- **Exponential Backoff**: `delay * base^retry_count`
- **Random Jitter**: Prevents thundering herd problems
- **Error Classification**: 7 types of LLM API errors
- **Rich Logging**: Detailed retry statistics and progress tracking
- **Configurable Parameters**: Flexible retry configuration

### 🎮 User Experience
- **Rich Terminal UI**: Beautiful formatting with live updates
- **Progress Tracking**: Visual feedback on retry attempts and success rates
- **Error Handling**: Clear error messages with suggestions

## 🏗️ Architecture

```
mermaid
graph TD
    A[Orange Code CLI] --> B[AgentScheduler] --> C[LLM Client]
    A[Tool Registry] --> D[Permission Guard] --> E[Tool Executor]
    A[Project Context] --> F[Core Agent Functions]
    A[Streaming Display] --> G[Rich Console UI]
    A[ESC Monitoring] --> H[User Input]
    A[Concurrency Control] --> I[Tool Execution]
```

## 📁 File Structure

```
📁 Orange Code/
├── 🤖 agent.py              # Main AI agent
├── 🛠️ utils.py              # Shared utility functions  
├── 🔄 retry.py             # LLM retry mechanism
├── 🧪 tool_executor.py      # Enhanced tool execution
├── 🎯 cli.py                # CLI entry point
├── 🧪 tests/                # Local testing environment
├── 📋 AGENTS.md              # Project context configuration
├── 📚 requirements.txt           # Dependencies
```

## 🚀 Deployment Options

- **Local Development** (Recommended)
- **No Container Overhead**: Direct execution
- **Fast Iteration**: Immediate code changes

## 🎮 User Experience

- **Rich Terminal UI**: Beautiful formatting with live updates
- **Progress Tracking**: Visual feedback on operations
- **Error Handling**: Clear messages and suggestions

## 📚 Benefits

- **Production Ready**: Enterprise-grade error handling and reliability
- **Developer Friendly**: Simple CLI with rich documentation
- **High Performance**: Optimized for local execution
- **Maintainable**: Clean, focused codebase
- **Secure**: Permission-based tool access control
- **Concurrent Safe**: Intelligent concurrency management