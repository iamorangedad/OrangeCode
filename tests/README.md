# Orange Code Test Environment

## Quick Start

```bash
# Start Orange Code in test environment
./run.sh

# Or run directly
python3 orangecode.py
```

## Environment

- **Python**: 3.11+
- **Dependencies**: uv package manager
- **LLM**: Ollama with qwen2.5-coder:3b model

## Configuration

Edit `.env` file to configure:

```
OLLAMA_HOST=http://10.0.0.55:11434
OLLAMA_MODEL=qwen2.5-coder:3b
```

## Testing

The test environment provides:
- Complete dependency management via uv
- Isolated Python environment
- Quick setup and execution

## Notes

- Make sure Ollama is running before starting
- The system will automatically load project context from AGENTS.md
- Choose your skill level when prompted