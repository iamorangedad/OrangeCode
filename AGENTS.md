# AI Agent Configuration

## Project Overview
Orange Code is a minimal coding agent. It completes small coding tasks by calling tools, then answering in text.

## Technology Stack
- Python 3.11
- An OpenAI-compatible chat endpoint (local Ollama `/v1` or an external gateway)
- Optional stdio MCP server for extra tools

## Code Standards
- Use Python type hints
- Follow PEP 8
- Document functions with docstrings
- Handle exceptions and return tool errors as text the model can read

## Common Commands
- Run the agent: `python3 orangecode.py`
- Show settings: `python3 orangecode.py --config`
- Tests: `python3 -m pytest`

## Project Structure
```
orangecode.py   # CLI entry point
agent.py        # Tool-calling loop
llm.py          # OpenAI-compatible client
tools.py        # read_file, write_file, list_files, execute_shell
mcp_client.py   # stdio MCP client
tests/          # pytest suite
```

## Configuration
- `BASE_URL` or `OLLAMA_HOST`: model endpoint. A host without `/v1` gets `/v1` appended.
- `MODEL` or `OLLAMA_MODEL`: model name. Default `qwen2.5-coder:3b`.
- `API_KEY` or `OPENAI_API_KEY`: bearer token when the endpoint requires one.
- `MCP_COMMAND`: optional stdio MCP server command.
- `MAX_STEPS`: tool-calling rounds. Default 8.
- `CONFIRM_SHELL`: set to `1` to confirm shell commands.

## Tools
Built-in tools stay inside the current working directory. MCP tools use the `mcp_` prefix and are listed beside the built-in tools.
