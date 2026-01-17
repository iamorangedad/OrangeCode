# Orange Code - Advanced AI Coding Agent

A production-ready autonomous coding assistant with sophisticated scheduler functionality, lazy loading, streaming display, and project-aware context management.

## 🚀 Key Features

### 🎯 Advanced Scheduler Architecture
- **Lazy Loading**: Fast CLI startup with `_ensure_agent_initialized()`
- **Concurrency Control**: `asyncio.Semaphore(10)` prevents API overload
- **Streaming Display**: Real-time output with tool call synchronization
- **ESC Cancellation**: Immediate interrupt via non-blocking keyboard detection
- **Project Context**: Automatic loading of `AGENTS.md` for project awareness

### 🛠️ Available Tools
- `read_file(path)` - Read content from files
- `write_file(path, content)` - Write content to files
- `list_files()` - List files in current directory
- `run_command(command)` - Execute shell commands with confirmation

### 🎮 User Experience
- **Rich Terminal UI**: Beautiful formatting with live updates
- **Tool Synchronization**: Proper display of concurrent tool executions
- **Project-Aware Responses**: Context-aware assistance based on project stack
- **Safety First**: Confirmation required for dangerous operations

## 🏗️ Architecture

```
🎛️ CLI Interface (cli.py)
        ↓
🤖 AgentScheduler (agent_no_rag.py)
    ├── 🧠 Lazy Loading (_ensure_agent_initialized)
    ├── 📋 Project Context (AGENTS.md)
    ├── 🔄 Concurrency Control (Semaphore)
    ├── 📺 Streaming Display Manager
    └── ⚠️ ESC Key Monitoring (Cancellation)
        ↓
🛠️ Core Tools (utils.py)
        ↓
🤖 Ollama LLM (qwen2.5-coder:3b)
```

## 🚀 Quick Start

### Method 1: CLI Interface (Recommended)

```bash
# Single query
./cli.py "帮我写个 fibonacci 函数"

# Show configuration
./cli.py config

# Interactive mode
./cli.py
```

### Method 2: Direct Agent Usage

```bash
# With arguments
python agent_no_rag.py --config
python agent_no_rag.py --ollama-host http://custom:11434 "query"

# Interactive
python agent_no_rag.py
```

### Method 3: Local Testing with uv

```bash
cd tests/
uv run python ../agent_no_rag.py
```

## 🔧 Configuration

### Environment Variables

```bash
# Ollama server
export OLLAMA_HOST="http://10.0.0.55:11434"

# Buffered output
export PYTHONUNBUFFERED=1
```

### Project Context (AGENTS.md)

Create `AGENTS.md` in your project root to provide context:

```markdown
# AI Agent Configuration

## Technology Stack
- **Python 3.11** - Primary programming language
- **Ollama** - LLM inference with qwen2.5-coder:3b model
- **Rich** - Terminal UI and formatting

## Code Standards
- Use Python type hints where possible
- Follow PEP 8 style guidelines
- Document functions with docstrings

## Common Commands
- **Testing**: `uv run python test_environment.py`
- **Dependencies**: `uv add package-name`
```

## 🐳 Deployment

### Kubernetes

```bash
# Deploy agent
kubectl apply -k deploy/

# Check deployment
kubectl get all -n orange-code

# Access logs
kubectl logs -f deployment/agent-no-rag -n orange-code
```

### Docker

```bash
# Build image
cd deploy/
docker build -t orange-code-agent .

# Run container
docker run -it --rm \
  -e OLLAMA_HOST=http://10.0.0.55:11434 \
  orange-code-agent
```

## 🧪 Testing

### Environment Testing

```bash
cd tests/
uv run python test_environment.py
```

### Manual Testing

```bash
# Test dependencies
uv run python -c "import ollama, rich, requests; print('✅ All deps OK')"

# Test Ollama connection
uv run python -c "import ollama; print(ollama.Client(host='http://10.0.0.55:11434').list())"
```

## 📁 Project Structure

```
Orange Code/
├── 🤖 agent_no_rag.py          # Main agent with scheduler
├── 🎯 cli.py                    # CLI entry point
├── 🛠️ utils.py                  # Shared utilities
├── 🧪 tests/                    # Testing environment
│   ├── run.sh                   # Test runner
│   ├── test_environment.py       # Environment validation
│   ├── pyproject.toml           # uv project config
│   └── .env                     # Test environment
├── 🚀 deploy/                   # Deployment assets
│   ├── Dockerfile               # Container build
│   ├── agent-config.yaml        # Kubernetes ConfigMap
│   ├── agent-no-rag-deployment.yaml  # Deployment
│   └── kustomization.yaml       # Kustomize config
├── 📋 AGENTS.md                # Project context
├── 📦 requirements_no_rag.txt    # Dependencies
├── 📚 AGENT_STRUCTURE.md       # Architecture docs
└── 📖 SCHEDULER_DESIGN.md      # Scheduler implementation
```

## 🎯 Usage Examples

### Basic Function Creation

```bash
./cli.py "Write a Python function to calculate fibonacci numbers"
```

### File Operations

```bash
./cli.py "Read the main.py file and add logging"
./cli.py "Create a new file called config.py with configuration"
```

### Project Management

```bash
./cli.py "Set up a proper Python project structure"
./cli.py "Add requirements.txt with necessary dependencies"
```

## 🎮 Interactive Commands

When running in interactive mode:

```bash
You: stats
📊 Shows session statistics (messages, tools used, duration)

You: clear  
🧹 Clears conversation history

You: quit / exit
👋 Exits the agent

You: [ESC]
🛑 Cancels current operation immediately
```

## 📊 Performance

### Resource Usage
- **Memory**: ~512MB steady state
- **CPU**: Low during idle, moderate during tool execution
- **Startup**: <2 seconds (lazy loading)
- **Response Time**: 2-5 seconds (depends on LLM model)

### Concurrency
- **Max Concurrent**: 10 requests (configurable)
- **API Protection**: Semaphore prevents overload
- **Graceful Degradation**: Queue management during high load

## 🛡️ Safety Features

### Command Execution Safety
- **Confirmation Required**: All shell commands need user approval
- **Clear Display**: Shows exact command to be executed
- **Abort Option**: Users can cancel dangerous operations

### Data Protection
- **No Persistent Storage**: Conversation history in memory only
- **Session Isolation**: No cross-session data leakage
- **Local Operations**: No external API calls except Ollama

## 🚨 Troubleshooting

### Ollama Connection Issues

```bash
# Test connection
curl http://10.0.0.55:11434/api/tags

# Check model availability
curl http://10.0.0.55:11434/api/tags | jq

# Verify model
uv run python -c "import ollama; print(ollama.Client().list())"
```

### Dependencies Issues

```bash
# Reinstall dependencies
cd tests/
uv sync --reinstall

# Check installed packages
uv pip list
```

### Permission Issues

```bash
# Make CLI executable
chmod +x cli.py

# Make test script executable  
chmod +x tests/run.sh
```

### ESC Key Not Working

```bash
# Ensure running in proper terminal
# ESC cancellation works in Unix terminals only
# Check if stdin is properly connected
```

## 🔧 Advanced Configuration

### Customizing Model

```bash
# Set different model
export OLLAMA_MODEL="llama2"
./cli.py "Your query here"

# Or pass via CLI
python agent_no_rag.py --ollama-host http://custom:11434 "query"
```

### Concurrency Tuning

Edit `agent_no_rag.py` to change semaphore limit:

```python
# In AgentScheduler.__init__
self.semaphore = asyncio.Semaphore(5)  # Reduce from 10 to 5
```

### Conversation History Limit

Change history retention in `build_history_aware_prompt()`:

```python
for msg in conversation_history[-5:]:  # Change from 10 to 5
```

## 🚀 Extension Ideas

### Potential Enhancements
- **Multiple Model Support**: Choose between different LLM models
- **Plugin System**: Dynamic tool loading
- **Web Interface**: Browser-based agent interaction
- **Persistent History**: Option to save/load conversations
- **Code Analysis**: AST-based code understanding
- **Git Integration**: Repository-aware assistance

### Contributing
Feel free to implement these features and submit pull requests!

## 📝 License

MIT License - Feel free to use and modify for your projects.

## 🤝 Contributing

Issues and Pull Requests are welcome! Please see the development guidelines in `AGENTS.md`.

---

**Orange Code** - Where AI meets real-world coding productivity. 🚀