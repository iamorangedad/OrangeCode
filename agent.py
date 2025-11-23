import os
import json
import subprocess
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich import box

# Initialize Rich console
console = Console()

# --- 1. Define Tools ---


def read_file(path):
    """Read file content with error handling"""
    try:
        if not os.path.exists(path):
            return "Error: File not found."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path, content):
    """Write content to file with error handling"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_files():
    """List files in current directory"""
    return str(os.listdir("."))


def run_command(command):
    """Execute shell command with safety confirmation"""
    # Display safety warning with Rich
    console.print(
        Panel(
            f"[yellow]Command:[/yellow] [cyan]{command}[/cyan]",
            title="⚠️  Safety Check",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    # Ask for confirmation
    confirm = Confirm.ask("Allow execution?", default=False)
    if not confirm:
        return "Error: User denied command execution."

    try:
        # Run command with timeout
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"


# --- 2. System Prompt ---

system_prompt = """
You are an autonomous coding agent. You have access to the following tools:

1. read_file: Reads the content of a file. Args: path (string)
2. write_file: Writes content to a file. Args: path (string), content (string)
3. list_files: Lists files in the current directory. No args.
4. run_command: Executes a shell command. Args: command (string)

When you need to use a tool, you MUST output the request in strict JSON format.
Example: {"tool": "write_file", "args": {"path": "hello.py", "content": "print('hello')"}}

Do not output any other text when calling a tool. Only the JSON.
"""

# Initialize conversation history
messages = [{"role": "system", "content": system_prompt}]

# --- 3. Display Welcome Screen ---
console.clear()
console.print(
    Panel.fit(
        "[bold cyan]Local Autonomous Coding Agent[/bold cyan]\n"
        "[dim]Powered by Ollama + Rich[/dim]",
        border_style="cyan",
        box=box.DOUBLE,
    )
)

# Display available tools table
tools_table = Table(title="Available Tools", box=box.ROUNDED, border_style="green")
tools_table.add_column("Tool", style="cyan", no_wrap=True)
tools_table.add_column("Description", style="white")
tools_table.add_row("read_file", "Read content from a file")
tools_table.add_row("write_file", "Write content to a file")
tools_table.add_row("list_files", "List files in current directory")
tools_table.add_row("run_command", "Execute shell commands")
console.print(tools_table)
console.print("[dim]Type 'quit' or 'exit' to stop[/dim]\n")

# --- 4. Main Loop ---
while True:
    client = ollama.Client(host="http://10.0.0.26:11434")
    MODEL_NAME = "qwen2.5-coder:0.5b"

    # Get user input with Rich prompt
    user_input = Prompt.ask("\n[bold green]You[/bold green]")

    if user_input.lower() in ["quit", "exit"]:
        console.print(
            Panel("[bold yellow]Goodbye! 👋[/bold yellow]", border_style="yellow")
        )
        break

    messages.append({"role": "user", "content": user_input})

    # Show thinking indicator
    with console.status("[bold cyan]Agent is thinking...[/bold cyan]", spinner="dots"):
        try:
            response = client.chat(model=MODEL_NAME, messages=messages)
        except Exception as e:
            console.print(f"[bold red]Ollama Error:[/bold red] {e}")
            continue

    content = response["message"]["content"]

    # --- 5. Tool Detection & Execution ---
    if '{"tool":' in content:
        try:
            # Clean up JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            # Extract JSON object
            start_idx = json_str.find("{")
            end_idx = json_str.rfind("}") + 1
            clean_json = json_str[start_idx:end_idx]

            parsed_json = json.loads(clean_json)
            tool_name = parsed_json.get("tool")
            args = parsed_json.get("args", {})

            # Display tool call information
            console.print(
                Panel(
                    f"[yellow]Tool:[/yellow] [bold cyan]{tool_name}[/bold cyan]\n"
                    f"[yellow]Args:[/yellow] {json.dumps(args, indent=2)}",
                    title="🔧 Tool Execution",
                    border_style="blue",
                    box=box.ROUNDED,
                )
            )

            # Execute tool
            result = "Error: Tool not found"
            if tool_name == "read_file":
                result = read_file(args.get("path"))
            elif tool_name == "write_file":
                result = write_file(args.get("path"), args.get("content"))
            elif tool_name == "list_files":
                result = list_files()
            elif tool_name == "run_command":
                result = run_command(args.get("command"))

            # Display result
            if result.startswith("Error"):
                console.print(Panel(result, border_style="red", title="❌ Error"))
            else:
                console.print(Panel(result, border_style="green", title="✅ Result"))

            # Feed result back to LLM
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"Tool Execution Result: {result}"}
            )

            # Generate final response
            with console.status("[bold cyan]Interpreting results...[/bold cyan]"):
                final_response = client.chat(model=MODEL_NAME, messages=messages)
                final_content = final_response["message"]["content"]

            # Display agent response
            console.print(
                Panel(
                    Markdown(final_content),
                    title="🤖 Agent Response",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
            )
            messages.append({"role": "assistant", "content": final_content})

        except json.JSONDecodeError:
            console.print(
                "[bold red]System:[/bold red] Failed to parse tool call JSON."
            )
            console.print(
                Panel(
                    content, title="Raw Output", border_style="yellow", box=box.ROUNDED
                )
            )
    else:
        # No tool called, display normal chat response
        console.print(
            Panel(
                Markdown(content),
                title="🤖 Agent",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        messages.append({"role": "assistant", "content": content})
