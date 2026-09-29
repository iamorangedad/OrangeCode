# Orange Code tests

```bash
python3 -m pytest
python3 test_tools.py
python3 test_llm.py
python3 test_agent.py
python3 test_mcp.py
```

From this directory, `./run.sh` starts the agent in the project root.

Configure the model with `BASE_URL` and `MODEL`. `OLLAMA_HOST` is used when `BASE_URL` is unset.
