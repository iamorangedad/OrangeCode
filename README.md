# Local Code Agent

A terminal-based AI coding assistant inspired by **Claude Code**. This tool runs locally using Python and connects to an Ollama server (local or remote) to edit files, run shell commands, and assist with development tasks.

## Features

  * **💬 Chat Interface**: Interact with the AI directly in your terminal.
  * **📂 File Management**: The agent can `read`, `write`, and `list` files in the current directory.
  * **🛠️ Command Execution**: Can execute shell commands (with a safety "Human-in-the-loop" confirmation).
  * **🔒 Private & Local**: Powered by open-source models (like Qwen 2.5 Coder) via Ollama.

## Prerequisites

  * **Python 3.8+**
  * **Ollama** (running locally or on a remote server)

## Installation

1.  **Clone or create the script**
    Save the agent code as `agent.py`.

2.  **Install dependencies**
    You only need the official Ollama Python library:

    ```bash
    pip install ollama
    ```

3.  **Prepare the Model**
    Make sure your Ollama instance has a coding model installed (e.g., Qwen 2.5 Coder):

    ```bash
    ollama pull qwen2.5-coder:7b
    ```

## Usage

Run the agent in your terminal:

```bash
python agent.py
```

### Example Commands

  * *"Create a file named `hello.py` that prints 'Hello World'."*
  * *"Read `main.py` and explain what it does."*
  * *"Run the python script I just created."* (Will trigger a safety confirmation)

## Configuration

### Connecting to a Remote Server

If your Ollama server is running on a different machine, you need to modify the `agent.py` file.

Change the initialization line:

```python
import ollama

# Connect to remote Ollama instance
client = ollama.Client(host='http://localhost:11434')

# Update the chat call loop to use 'client.chat' instead of 'ollama.chat'
response = client.chat(model='qwen2.5-coder:7b', messages=messages)
```

> **Note:** Ensure your remote Ollama service is configured to listen on `0.0.0.0` (see service configuration).

## ⚠️ Safety Disclaimer

This agent has access to your file system and terminal.

  * **Always review** the code the agent wants to write.
  * **Always check** the shell commands before confirming execution (`y/n`).
  * Do not run this in a root directory or sensitive production environment without sandboxing (e.g., Docker).

-----

### License

MIT License