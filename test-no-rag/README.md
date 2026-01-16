# No-RAG Agent Test Environment

This directory contains a complete uv-based testing environment for the no-RAG agent.

## Quick Setup

### 1. Initialize Environment
```bash
cd test-no-rag
python3 setup.py
```

### 2. Run the Agent
```bash
./run.sh
```

## Manual Setup

### 1. Install Dependencies
```bash
uv add ollama rich requests
```

### 2. Configure Ollama Host
```bash
export OLLAMA_HOST="http://10.0.0.55:11434"
# or create .env file:
echo "OLLAMA_HOST=http://10.0.0.55:11434" > .env
```

### 3. Run the Agent
```bash
uv run python agent_no_rag.py
```

## Testing

### Test Environment
```bash
uv run python test_environment.py
```

### Test Individual Components
```bash
# Test dependencies
uv run python -c "import ollama, rich, requests; print('✅ All deps OK')"

# Test Ollama connection
uv run python -c "import ollama; print(ollama.Client(host='http://10.0.0.55:11434').list())"
```

## Files

- `agent_no_rag.py` - Main agent script
- `utils.py` - Utility functions
- `setup.py` - Environment setup script
- `test_environment.py` - Environment validation script
- `run.sh` - Convenient run script
- `.env` - Environment configuration (created by setup)
- `pyproject.toml` - uv project configuration

## Usage Examples

Once the agent is running:

```
You: Read the main.py file
🤖 Agent: Reading main.py...

You: Create a hello world function
🤖 Agent: Creating function...

You: quit
```

## Troubleshooting

### Ollama Connection Failed
1. Ensure Ollama is running: `ollama serve`
2. Check the host URL in `.env` file
3. Test connection: `curl http://10.0.0.55:11434/api/tags`

### Dependencies Issues
```bash
# Reinstall dependencies
uv sync --reinstall
```

### Permission Denied
```bash
# Make run script executable
chmod +x run.sh
```