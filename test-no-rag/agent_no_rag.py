import os
import json
import subprocess
import ollama
import requests
import uuid
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich import box
from utils import read_file, write_file, list_files, execute_command

# Initialize Rich console
console = Console()

# In-memory conversation history
conversation_history = []


def run_command(command):
    """Execute shell command with safety confirmation"""
    console.print(
        Panel(
            f"[yellow]Command:[/yellow] [cyan]{command}[/cyan]",
            title="⚠️  Safety Check",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )
    confirm = Confirm.ask("Allow execution?", default=False)
    if not confirm:
        return "Error: User denied command execution."
    execute_command(command)


def build_history_aware_prompt(user_query: str) -> str:
    """Build prompt with conversation history"""

    prompt_parts = [
        "You are an autonomous coding agent with access to conversation history.",
        "\n--- TOOLS AVAILABLE ---",
    ]

    # Add tool descriptions
    prompt_parts.append(
        """
        1. read_file: Reads the content of a file. Args: path (string)
        2. write_file: Writes content to a file. Args: path (string), content (string)
        3. list_files: Lists files in the current directory. No args.
        4. run_command: Executes a shell command. Args: command (string)

        When using a tool, output ONLY JSON format:
        {"tool": "tool_name", "args": {"arg_name": "value"}}
    """
    )

    # Add conversation history
    if conversation_history:
        prompt_parts.append("\n--- CONVERSATION HISTORY ---")
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg["role"]
            prompt_parts.append(f"{role}: {msg['content']}")

    # Add current query
    prompt_parts.append(f"\n--- CURRENT REQUEST ---\nUser: {user_query}")

    return "\n".join(prompt_parts)


console.clear()
console.print(
    Panel.fit(
        "[bold cyan]Autonomous Coding Agent[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE,
    )
)
tools_table = Table(title="Available Tools", box=box.ROUNDED, border_style="green")
tools_table.add_column("Tool", style="cyan", no_wrap=True)
tools_table.add_column("Description", style="white")
tools_table.add_row("read_file", "Read content from a file")
tools_table.add_row("write_file", "Write content to a file")
tools_table.add_row("list_files", "List files in current directory")
tools_table.add_row("run_command", "Execute shell commands")
console.print(tools_table)
console.print(
    "\n[dim]Commands: 'quit'/'exit' to stop, 'stats' for session stats, 'clear' to clear history[/dim]\n"
)

while True:
    client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://10.0.0.56:11434"))
    user_input = Prompt.ask("\n[bold green]You[/bold green]")
    if user_input.lower() in ["quit", "exit"]:
        console.print(
            Panel(
                f"Session ended\nTotal messages: {len(conversation_history)}",
                border_style="yellow",
            )
        )
        console.print(
            Panel("[bold yellow]Goodbye! 👋[/bold yellow]", border_style="yellow")
        )
        break
    if user_input.lower() == "stats":
        stats_table = Table(title=f"Session Statistics", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        stats_table.add_row("Total Messages", str(len(conversation_history)))
        console.print(stats_table)
        continue
    if user_input.lower() == "clear":
        if Confirm.ask("Clear all history for this session?", default=False):
            conversation_history = []
            console.print("[bold green]History cleared[/bold green]")
        continue
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history = conversation_history[-10:]
    context_prompt = build_history_aware_prompt(user_input)
    with console.status("[bold cyan]Agent is thinking...[/bold cyan]", spinner="dots"):
        try:
            response = client.chat(
                model="qwen2.5-coder:3b",
                messages=[
                    {"role": "system", "content": context_prompt},
                    {"role": "user", "content": user_input},
                ],
            )
        except Exception as e:
            console.print(f"[bold red]Ollama Error:[/bold red] {e}")
            continue
    content = response["message"]["content"]

    # --- Tool Detection & Execution ---
    if '{"tool":' in content:
        try:
            # Parse JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            start_idx = json_str.find("{")
            end_idx = json_str.rfind("}") + 1
            clean_json = json_str[start_idx:end_idx]

            parsed_json = json.loads(clean_json)
            tool_name = parsed_json.get("tool")
            args = parsed_json.get("args", {})

            # Display tool call
            console.print(
                Panel(
                    f"[yellow]Tool:[/yellow] [bold cyan]{tool_name}[/bold cyan]\n"
                    f"[yellow]Args:[/yellow] {json.dumps(args, indent=2)}",
                    title="🔧 Tool Execution",
                    border_style="blue",
                    box=box.ROUNDED,
                )
            )

            # Store tool call in history
            conversation_history.append({"role": "assistant", "content": content})
            conversation_history = conversation_history[-10:]

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
            if result and result.startswith("Error"):
                console.print(Panel(result, border_style="red", title="❌ Error"))
            else:
                console.print(
                    Panel(
                        (result or "")[:500]
                        + ("..." if len(result or "") > 500 else ""),
                        border_style="green",
                        title="✅ Result",
                    )
                )

            # Store tool result
            conversation_history.append(
                {"role": "system", "content": f"Tool '{tool_name}' result: {result}"}
            )
            conversation_history = conversation_history[-10:]

            # Get final interpretation with history
            final_prompt = build_history_aware_prompt(
                f"Interpret the result of {tool_name}: {(result or '')[:200]}"
                if result
                else "Tool failed"
            )

            with console.status("[bold cyan]Interpreting results...[/bold cyan]"):
                final_response = client.chat(
                    model="qwen2.5-coder:3b",
                    messages=[
                        {"role": "system", "content": final_prompt},
                        {"role": "user", "content": f"Tool result: {result}"},
                    ],
                )
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

            # Store final response
            conversation_history.append({"role": "assistant", "content": final_content})
            conversation_history = conversation_history[-10:]

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

        # Store response in history
        conversation_history.append({"role": "assistant", "content": content})
        conversation_history = conversation_history[-10:]
