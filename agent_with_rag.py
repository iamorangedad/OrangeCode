"""
Enhanced Code Agent with RAG Context Management
Integrates with context microservice for intelligent history retrieval
"""

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

# Initialize Rich console
console = Console()

# Configuration
CONTEXT_SERVICE_URL = os.getenv("CONTEXT_SERVICE_URL", "http://localhost:8000")
SESSION_ID = str(uuid.uuid4())
MAX_CONTEXT_ITEMS = 5  # Number of relevant context items to retrieve


# =================================================================
# ==================== Context Service Client =====================
# =================================================================
class ContextClient:
    """Client for interacting with context management service"""

    def __init__(self, base_url: str, session_id: str):
        self.base_url = base_url
        self.session_id = session_id

    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add a message to context storage"""
        try:
            response = requests.post(
                f"{self.base_url}/context/add",
                json={
                    "session_id": self.session_id,
                    "message": {
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": metadata or {},
                    },
                },
                timeout=5,
            )
            return response.json() if response.ok else None
        except Exception as e:
            console.print(f"[dim red]Context service error: {e}[/dim red]")
            return None

    def query_relevant_context(self, query: str, top_k: int = 5):
        """Query relevant context based on semantic similarity"""
        try:
            response = requests.post(
                f"{self.base_url}/context/query",
                json={"session_id": self.session_id, "query": query, "top_k": top_k},
                timeout=5,
            )
            if response.ok:
                return response.json()["messages"]
            return []
        except Exception as e:
            console.print(f"[dim red]Context query error: {e}[/dim red]")
            return []

    def get_recent_context(self, limit: int = 5):
        """Get recent conversation history"""
        try:
            response = requests.post(
                f"{self.base_url}/context/recent",
                params={"session_id": self.session_id, "limit": limit},
                timeout=5,
            )
            if response.ok:
                return response.json()["messages"]
            return []
        except Exception as e:
            console.print(f"[dim red]Recent context error: {e}[/dim red]")
            return []

    def get_stats(self):
        """Get session statistics"""
        try:
            response = requests.get(
                f"{self.base_url}/context/stats/{self.session_id}", timeout=5
            )
            return response.json() if response.ok else None
        except Exception as e:
            return None


# Initialize context client
context_client = ContextClient(CONTEXT_SERVICE_URL, SESSION_ID)


# =================================================================
# ==================== Tool Functions =============================
# =================================================================
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

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"


# =================================================================
# ==================== Context-Aware Prompt Builder ===============
# =================================================================
def build_context_aware_prompt(user_query: str) -> str:
    """Build prompt with relevant context from RAG"""

    # Get relevant context
    relevant_contexts = context_client.query_relevant_context(
        user_query, top_k=MAX_CONTEXT_ITEMS
    )

    # Get recent context for continuity
    recent_contexts = context_client.get_recent_context(limit=3)

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

    # Add relevant historical context
    if relevant_contexts:
        prompt_parts.append("\n--- RELEVANT CONTEXT FROM HISTORY ---")
        for ctx in relevant_contexts[:3]:  # Limit to top 3
            content_preview = (
                ctx["content"][:200] + "..."
                if len(ctx["content"]) > 200
                else ctx["content"]
            )
            prompt_parts.append(
                f"[{ctx['metadata'].get('type', 'unknown')}] {content_preview}"
            )

    # Add recent conversation for continuity
    if recent_contexts:
        prompt_parts.append("\n--- RECENT CONVERSATION ---")
        for ctx in reversed(recent_contexts):  # Chronological order
            role = ctx["metadata"].get("role", "unknown")
            content_preview = (
                ctx["content"][:150] + "..."
                if len(ctx["content"]) > 150
                else ctx["content"]
            )
            prompt_parts.append(f"{role}: {content_preview}")

    # Add current query
    prompt_parts.append(f"\n--- CURRENT REQUEST ---\nUser: {user_query}")

    return "\n".join(prompt_parts)


# =================================================================
# ==================== Display Welcome Screen =====================
# =================================================================
console.clear()
console.print(
    Panel.fit(
        "[bold cyan]RAG-Enhanced Autonomous Coding Agent[/bold cyan]\n"
        f"[dim]Session ID: {SESSION_ID[:8]}...[/dim]\n"
        f"[dim]Context Service: {CONTEXT_SERVICE_URL}[/dim]",
        border_style="cyan",
        box=box.DOUBLE,
    )
)

# Display available tools
tools_table = Table(title="Available Tools", box=box.ROUNDED, border_style="green")
tools_table.add_column("Tool", style="cyan", no_wrap=True)
tools_table.add_column("Description", style="white")
tools_table.add_row("read_file", "Read content from a file")
tools_table.add_row("write_file", "Write content to a file")
tools_table.add_row("list_files", "List files in current directory")
tools_table.add_row("run_command", "Execute shell commands")
console.print(tools_table)

# Check context service connection
with console.status("[bold cyan]Connecting to context service...[/bold cyan]"):
    try:
        response = requests.get(f"{CONTEXT_SERVICE_URL}/", timeout=3)
        if response.ok:
            console.print("[bold green]✓[/bold green] Context service connected")
        else:
            console.print(
                "[bold yellow]⚠[/bold yellow] Context service unavailable (running in degraded mode)"
            )
    except:
        console.print(
            "[bold yellow]⚠[/bold yellow] Context service unavailable (running in degraded mode)"
        )

console.print(
    "\n[dim]Commands: 'quit'/'exit' to stop, 'stats' for session stats, 'clear' to clear context[/dim]\n"
)


# =================================================================
# ============================= Main Loop =========================
# =================================================================
while True:
    client = ollama.Client(host="http://10.0.0.26:11434")

    # Get user input
    user_input = Prompt.ask("\n[bold green]You[/bold green]")

    # Handle special commands
    if user_input.lower() in ["quit", "exit"]:
        stats = context_client.get_stats()
        if stats:
            console.print(
                Panel(
                    f"Session ended\nTotal messages: {stats.get('total_messages', 0)}",
                    border_style="yellow",
                )
            )
        console.print(
            Panel("[bold yellow]Goodbye! 👋[/bold yellow]", border_style="yellow")
        )
        break

    if user_input.lower() == "stats":
        stats = context_client.get_stats()
        if stats:
            stats_table = Table(title=f"Session Statistics", box=box.ROUNDED)
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="white")
            stats_table.add_row("Total Messages", str(stats.get("total_messages", 0)))
            for msg_type, count in stats.get("by_type", {}).items():
                stats_table.add_row(f"  {msg_type}", str(count))
            console.print(stats_table)
        continue

    if user_input.lower() == "clear":
        if Confirm.ask("Clear all context for this session?", default=False):
            requests.post(
                f"{CONTEXT_SERVICE_URL}/context/clear", json={"session_id": SESSION_ID}
            )
            console.print("[bold green]Context cleared[/bold green]")
        continue

    # Store user message in context
    context_client.add_message("user", user_input, {"type": "user_query"})

    # Build context-aware prompt
    context_prompt = build_context_aware_prompt(user_input)

    # Get LLM response
    with console.status(
        "[bold cyan]Agent is thinking (with context)...[/bold cyan]", spinner="dots"
    ):
        try:
            response = client.chat(
                model="qwen2.5-coder:0.5b",
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

            # Store tool call in context
            context_client.add_message(
                "assistant", content, {"type": "tool_call", "tool_name": tool_name}
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
                console.print(
                    Panel(
                        result[:500] + ("..." if len(result) > 500 else ""),
                        border_style="green",
                        title="✅ Result",
                    )
                )

            # Store tool result
            context_client.add_message(
                "system",
                f"Tool '{tool_name}' result: {result}",
                {"type": "tool_result", "tool_name": tool_name},
            )

            # Get final interpretation with context
            final_prompt = build_context_aware_prompt(
                f"Interpret the result of {tool_name}: {result[:200]}"
            )

            with console.status("[bold cyan]Interpreting results...[/bold cyan]"):
                final_response = client.chat(
                    model="qwen2.5-coder:0.5b",
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
            context_client.add_message(
                "assistant", final_content, {"type": "agent_response"}
            )

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

        # Store response in context
        context_client.add_message("assistant", content, {"type": "agent_response"})
