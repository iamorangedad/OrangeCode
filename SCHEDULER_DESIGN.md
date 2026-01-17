# Agent Scheduler Implementation

## Overview

The `agent_no_rag.py` has been completely redesigned with advanced scheduler functionality based on modern AI agent patterns.

## 🚀 Key Features

### 1. Lazy Loading with `_ensure_agent_initialized()`
Agent initializes only when needed, not on startup:
- Lightweight CLI entry (`orangecode config show`)
- Heavy initialization (LLM client, tools) happens on first message
- Reduces startup time and resource usage

### 2. CLI Entry Point with Project Context
```bash
./cli.py "帮我写个XXX函数"
```
- Parses arguments via `argparse`
- Loads `AGENTS.md` as project context (tech stack, standards, commands)
- Provides project-aware assistance

### 3. Concurrency Control
- `asyncio.Semaphore(10)` limits concurrent requests
- Prevents API overload
- Ensures controlled resource usage

### 4. Streaming Display Management
`StreamingDisplayManager` handles complex output scenarios:

#### Tool Call Synchronization
- `pending_tool_calls` counter tracks active tool executions
- Text displayed only when `pending_tool_calls == 0`
- Tool execution期间的文字先accumulated，工具完成后一起输出

#### Tool Result Matching
- `active_tool_calls[call_id]` dictionary maps calls to results
- Supports proper call/result pairing
- Falls back to FIFO for models without call IDs

#### Rich Live Display
- Real-time output with `rich.Live`
- Status updates during tool execution
- Smooth user experience

### 5. ESC Key Cancellation
- Non-blocking keyboard detection via `select.select()`
- Immediate interrupt capability
- Graceful cancellation with cleanup
- Critical user experience enhancement

## 🏗️ Architecture

```
cli.py (Entry Point)
    ↓
AgentScheduler (Orchestration)
    ├── Lazy Loading (_ensure_agent_initialized)
    ├── Project Context Loading (AGENTS.md)
    ├── Concurrency Control (Semaphore)
    ├── StreamingDisplayManager (Output Management)
    └── ESC Key Monitoring (Cancellation)
```

## 📁 File Structure

### New Components
- `cli.py` - CLI entry point with argument parsing
- `agent_no_rag.py` - Completely rewritten with scheduler
- `AGENTS.md` - Project context file

### Core Classes
- `AgentScheduler` - Main orchestration and lazy loading
- `StreamingDisplayManager` - Stream output and tool synchronization

## 🔧 Usage

### CLI Mode
```bash
# Single query
./cli.py "帮我写个 fibonacci 函数"

# Show configuration
./cli.py config

# Interactive mode
./cli.py
```

### Direct Agent Usage
```bash
# With arguments
python agent_no_rag.py --config
python agent_no_rag.py --ollama-host http://custom:11434 "query"

# Interactive
python agent_no_rag.py
```

## 🎯 Benefits

1. **Performance**: Lazy loading reduces startup overhead
2. **Project Awareness**: AGENTS.md provides context
3. **Concurrency**: Semaphore prevents API overload
4. **User Experience**: Streaming + ESC cancellation
5. **Maintainability**: Clean separation of concerns

## 🔄 Flow Example

User runs: `./cli.py "帮我写个XXX函数"`

1. **CLI parses** arguments
2. **Scheduler lazy-loads** (first time only)
3. **Loads AGENTS.md** context (Python project, Rich, etc.)
4. **Processes streaming** response with tool calls
5. **Manages display** (text vs tool results)
6. **User can ESC-cancel** anytime

## 🛠️ Advanced Features

### Project Context Integration
- Automatically detects project type
- Provides relevant tool suggestions
- Follows project coding standards

### Tool Call Orchestration
- Parallel tool execution support
- Result aggregation and interpretation
- Error handling with fallbacks

### Resource Management
- Memory-efficient streaming
- Connection pooling
- Graceful shutdown handling

This scheduler implementation represents a production-ready AI agent architecture with advanced concurrency, user experience, and maintainability features.