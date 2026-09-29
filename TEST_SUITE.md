# Orange Code unit tests

Run everything from the project root:

```bash
python3 -m pytest
python3 tests/run_all_tests.py
```

Modules:

- `test_tools.py` checks workspace read, write, list, and shell tools
- `test_llm.py` checks the OpenAI-compatible client and retries
- `test_agent.py` checks the tool-calling loop
- `test_mcp.py` checks stdio framing and a fake MCP server
- `test_environment.py` checks that the core modules are present
