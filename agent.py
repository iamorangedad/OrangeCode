import os
import json
import re
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
from utils import extract_filename_from_code, get_unique_filename

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
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
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


# --- 2. Code Extraction & Processing ---


def extract_code_blocks(content):
    """Extract all code blocks from content"""
    pattern = r"```(\w+)?\n(.*?)\n```"
    matches = re.findall(pattern, content, re.DOTALL)
    return matches  # Returns list of tuples: (language, code)


def get_unique_filename(base_name):
    """Generate unique filename to avoid overwriting existing files"""
    if not os.path.exists(base_name):
        return base_name

    name, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(f"{name}_{counter}{ext}"):
        counter += 1
    return f"{name}_{counter}{ext}"


def process_response(content):
    """Process LLM response and extract code blocks"""
    code_blocks = extract_code_blocks(content)

    if code_blocks:
        files_created = []
        for idx, (lang, code) in enumerate(code_blocks):
            # Try to extract meaningful filename from code
            extracted_filename = extract_filename_from_code(code, lang)

            if lang in ["python", "py"]:
                base_filename = extracted_filename or f"generated_{idx}.py"
                filename = get_unique_filename(base_filename)
                result = write_file(filename, code)
                files_created.append((filename, lang, result))
                console.print(
                    Panel(
                        Syntax(code, "python", theme="monokai", line_numbers=True),
                        title=f"📝 Code Block ({lang})",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                )
                console.print(
                    Panel(result, border_style="green", title="✅ File Creation Result")
                )
            elif lang in ["javascript", "js", "typescript", "ts"]:
                base_filename = extracted_filename or f"generated_{idx}.js"
                filename = get_unique_filename(base_filename)
                result = write_file(filename, code)
                files_created.append((filename, lang, result))
                console.print(
                    Panel(
                        Syntax(code, "javascript", theme="monokai", line_numbers=True),
                        title=f"📝 Code Block ({lang})",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                )
                console.print(
                    Panel(result, border_style="green", title="✅ File Creation Result")
                )
            elif lang in ["bash", "shell", "sh"]:
                base_filename = extracted_filename or f"generated_{idx}.sh"
                filename = get_unique_filename(base_filename)
                result = write_file(filename, code)
                files_created.append((filename, lang, result))
                console.print(
                    Panel(
                        Syntax(code, "bash", theme="monokai", line_numbers=True),
                        title=f"📝 Code Block ({lang})",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                )
                console.print(
                    Panel(result, border_style="green", title="✅ File Creation Result")
                )

        return files_created
    return []


# --- 3. Initialize Conversation ---

# Initialize conversation history (no system prompt needed)
messages = []

# Initialize Ollama client
client_instance = None

# --- 4. Display Welcome Screen ---
console.clear()
console.print(
    Panel.fit(
        "[bold cyan]Local Autonomous Coding Agent[/bold cyan]\n"
        "[dim]Powered by Ollama + Rich[/dim]",
        border_style="cyan",
        box=box.DOUBLE,
    )
)

tools_table = Table(title="Available Features", box=box.ROUNDED, border_style="green")
tools_table.add_column("Feature", style="cyan", no_wrap=True)
tools_table.add_column("Description", style="white")
tools_table.add_row("Code Generation", "Generate and save code from your requests")
tools_table.add_row("Auto File Creation", "Automatically create Python, JS, Bash files")
tools_table.add_row("Code Display", "Syntax-highlighted code preview")
tools_table.add_row("Conversation History", "Maintain context across multiple requests")
console.print(tools_table)
console.print("[dim]Type 'quit' or 'exit' to stop[/dim]\n")

# --- 5. Main Loop ---
while True:
    client = ollama.Client(host="http://10.0.0.56:11434")

    user_input = Prompt.ask("\n[bold green]You[/bold green]")

    if user_input.lower() in ["quit", "exit"]:
        console.print(
            Panel("[bold yellow]Goodbye! 👋[/bold yellow]", border_style="yellow")
        )
        break

    messages.append({"role": "user", "content": user_input})

    with console.status("[bold cyan]Agent is thinking...[/bold cyan]", spinner="dots"):
        try:
            response = client.chat(model="qwen2.5-coder:0.5b", messages=messages)
        except Exception as e:
            console.print(f"[bold red]Ollama Error:[/bold red] {e}")
            messages.pop()
            continue

    content = response["message"]["content"]

    # --- 6. Process Response and Extract Code ---
    console.print(
        Panel(
            Markdown(content),
            title="🤖 Agent Response",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    # Extract and process code blocks
    files_created = process_response(content)

    if files_created:
        console.print(
            Panel(
                f"[green]Created {len(files_created)} file(s):[/green]\n"
                + "\n".join([f"  • {fn} ({lang})" for fn, lang, _ in files_created]),
                border_style="green",
                title="📦 Files Created",
            )
        )

    # Add to conversation history
    messages.append({"role": "assistant", "content": content})
