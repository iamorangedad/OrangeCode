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
tools.py        # read_file, write_file, edit_file, search, list_files, execute_shell
mcp_client.py   # stdio MCP client
tests/          # pytest suite
```

## Configuration
- `BASE_URL` or `OLLAMA_HOST`: model endpoint. A host without `/v1` gets `/v1` appended.
- `MODEL` or `OLLAMA_MODEL`: model name. Default `qwen2.5-coder:3b`.
- `API_KEY` or `OPENAI_API_KEY`: bearer token when the endpoint requires one.
- `MCP_COMMAND`: optional stdio MCP server command.
- `MCP_TIMEOUT`: seconds to wait for an MCP response. Default 30, maximum 120.
- `MAX_STEPS`: tool-calling rounds. Default 8.
- `CHECK_COMMAND`: command run after a request writes files and the model stops. A non-zero exit is sent back into the loop. Empty means no check.
- `SHELL`: `ask`, `allow`, or `deny`. Interactive sessions default to `ask`. One-shot runs default to `deny`. `orangecode.toml` can set `shell` when this variable is not one of those three words.
- `TRACE`: set to `0` to hide tool start and end lines on stderr.
- `CONFIRM_SHELL`: `1` means ask and `0` means allow, unless `SHELL` is exactly `ask`, `allow`, or `deny`.

## Tools
Built-in tools stay inside the current working directory. `read_file` without a line range refuses files longer than 400 lines. `read_file`, `write_file`, and `edit_file` refuse secret files and paths inside `.git` or `.orangecode`. `search` skips those paths. MCP tools use the `mcp_` prefix and are listed beside the built-in tools.
