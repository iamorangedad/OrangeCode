# Orange Code

A minimal coding agent. It reads and edits files, runs shell commands, and can call tools from one MCP server. The model can be a local Ollama instance or any OpenAI-compatible endpoint.

## Run

```bash
pip install -r requirements.txt

export BASE_URL="http://127.0.0.1:11434"
export MODEL="qwen2.5-coder:3b"
python3 orangecode.py
```

`BASE_URL` may be an Ollama host (`http://127.0.0.1:11434`) or a full `/v1` base URL. `OLLAMA_HOST` is still accepted when `BASE_URL` is unset. Set `API_KEY` or `OPENAI_API_KEY` for endpoints that require a bearer token.

```bash
python3 orangecode.py --config
python3 orangecode.py "Add a docstring to tools.py"
```

Interactive commands are `config` and `quit`.

## Tools

- `read_file` reads a text file, or a line range when `start_line` and `end_line` are set
- `search` finds text or a per-line regular expression and returns `path:line`
- `edit_file` replaces one unique snippet and reports the lines that changed
- `write_file` creates or overwrites a whole file
- `list_files` lists workspace entries
- `execute_shell` runs a command with the workspace as its working directory

`SHELL` controls `execute_shell`:

- interactive sessions default to `ask` and confirm each command
- `python3 orangecode.py "task"` defaults to `deny` and does not run a command
- `SHELL=allow` runs commands without a prompt
- `SHELL=deny` refuses them
- `CONFIRM_SHELL=1` still means ask, and `CONFIRM_SHELL=0` means allow. An explicit `SHELL` value wins
- `ask` with no terminal is treated as deny

An allowed command is still not a sandbox. It runs through the system shell with the workspace as its working directory.

`read_file`, `write_file`, and `edit_file` refuse `.env`, `.env.*`, `.netrc`, `id_rsa`, `id_dsa`, `credentials.json`, and files ending in `.pem`, `.key`, `.p12`, or `.pfx`. They also refuse anything under `.git` or `.orangecode`. `search` skips those paths.

`MAX_STEPS` limits tool rounds (default 8). `MCP_TIMEOUT` is the MCP read timeout in seconds (default 30, maximum 120).

## MCP

Set `MCP_COMMAND` to a stdio MCP server. Orange Code sends `initialize` and `tools/list` at startup, then `tools/call` when the model uses a tool. Server tools are exposed with an `mcp_` prefix.

```bash
export MCP_COMMAND="uvx mcp-server-filesystem /home/jetson/OrangeCode"
python3 orangecode.py
```

If the server fails to start, the agent continues with the built-in tools.

## Tests

```bash
python3 -m pytest
```

## Layout

```
orangecode.py    CLI
agent.py         tool-calling loop
llm.py           OpenAI-compatible chat client
tools.py         workspace tools
mcp_client.py    stdio MCP client
```
