#!/usr/bin/env python3
"""
No-RAG Agent with Scheduler functionality

Implements:
- Lazy loading with _ensure_agent_initialized()
- Concurrency control with asyncio.Semaphore(10)
- Streaming display management with tool call tracking
- ESC key cancellation support
- Project context loading from AGENTS.md
"""

import os
import sys
import json
import asyncio
import select
import signal
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Any, AsyncGenerator
from datetime import datetime
import threading

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text
from rich import box
from utils import read_file, write_file, list_files, execute_command


class StreamingDisplayManager:
    """Manages streaming output with tool call synchronization"""

    def __init__(self, console: Console):
        self.console = console
        self.pending_tool_calls = 0
        self.active_tool_calls = {}  # call_id -> tool_info
        self.accumulated_text = []
        self.live_display: Optional[Live] = None
        self.current_output = Text()

    def start_display(self):
        """Start the live display"""
        self.live_display = Live(
            self.current_output, console=self.console, refresh_per_second=10
        )
        self.live_display.start()

    def stop_display(self):
        """Stop the live display"""
        if self.live_display:
            self.live_display.stop()
            self.live_display = None

    def add_tool_call(self, call_id: str, tool_info: Dict[str, Any]):
        """Register a new tool call"""
        self.pending_tool_calls += 1
        self.active_tool_calls[call_id] = tool_info
        self._update_display(f"\n🔧 Calling {tool_info.get('tool', 'unknown')}...")

    def complete_tool_call(self, call_id: str, result: Any):
        """Complete a tool call"""
        if call_id in self.active_tool_calls:
            self.pending_tool_calls -= 1
            tool_info = self.active_tool_calls[call_id]
            del self.active_tool_calls[call_id]
            self._update_display(f"✅ {tool_info.get('tool', 'unknown')} completed")

    def add_text(self, text: str):
        """Add text to display (shown when no pending tool calls)"""
        if self.pending_tool_calls == 0:
            self._flush_accumulated()
            self.current_output.append(text)
            self._refresh_display()
        else:
            self.accumulated_text.append(text)

    def _flush_accumulated(self):
        """Flush accumulated text to display"""
        if self.accumulated_text:
            accumulated = "".join(self.accumulated_text)
            self.current_output.append(accumulated)
            self.accumulated_text.clear()

    def _update_display(self, status: str):
        """Update display with status message"""
        if self.pending_tool_calls > 0:
            temp = self.current_output.copy()
            temp.append(f"\n[dim]...{status}...[/dim]")
            if self.live_display:
                self.live_display.update(temp)

    def _refresh_display(self):
        """Refresh the live display"""
        if self.live_display:
            self.live_display.update(self.current_output)


class AgentScheduler:
    """Main scheduler with lazy loading and concurrency control"""

    def __init__(self):
        self.console = Console()
        self.client: Optional[ollama.Client] = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.project_context: str = ""
        self.semaphore = asyncio.Semaphore(10)
        self.display_manager = StreamingDisplayManager(self.console)
        self.is_cancelled = False
        self.keyboard_thread: Optional[threading.Thread] = None

        # Lazy loading flag
        self._agent_initialized = False

    def _ensure_agent_initialized(self):
        """Initialize agent on first use (lazy loading)"""
        if self._agent_initialized:
            return

        # Initialize Ollama client
        ollama_host = os.getenv("OLLAMA_HOST", "http://10.0.0.55:11434")
        self.client = ollama.Client(host=ollama_host)

        # Load project context
        self._load_project_context()

        # Start keyboard monitoring for ESC cancellation
        self._start_keyboard_monitor()

        self._agent_initialized = True
        self.console.print("✅ Agent initialized", style="green")

    def _load_project_context(self):
        """Load project context from AGENTS.md"""
        agents_file = Path("AGENTS.md")
        if agents_file.exists():
            try:
                self.project_context = agents_file.read_text(encoding="utf-8")
                self.console.print(
                    f"📋 Loaded project context from {agents_file}", style="blue"
                )
            except Exception as e:
                self.console.print(f"⚠️ Failed to load AGENTS.md: {e}", style="yellow")
                self.project_context = ""
        else:
            self.project_context = ""

    def _start_keyboard_monitor(self):
        """Start keyboard monitoring for ESC key cancellation"""

        def monitor_keyboard():
            while not self.is_cancelled:
                # Use select.select() for non-blocking keyboard detection
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    char = sys.stdin.read(1)
                    if char == "\x1b":  # ESC key
                        self.cancel_execution()
                        break

        self.keyboard_thread = threading.Thread(target=monitor_keyboard, daemon=True)
        self.keyboard_thread.start()

    def cancel_execution(self):
        """Cancel current execution"""
        self.is_cancelled = True
        self.console.print("\n🛑 Execution cancelled by user (ESC)", style="red")
        self.display_manager.stop_display()

    def _build_prompt(self, user_query: str) -> str:
        """Build prompt with project context and conversation history"""
        prompt_parts = [
            "You are an autonomous coding agent with access to file system tools.",
        ]

        # Add project context if available
        if self.project_context:
            prompt_parts.append("\n--- PROJECT CONTEXT ---")
            prompt_parts.append(self.project_context)

        prompt_parts.extend(
            [
                "\n--- TOOLS AVAILABLE ---",
                "- read_file(path): Read content from a file",
                "- write_file(path, content): Write content to a file",
                "- list_files(): List files in current directory",
                "- run_command(command): Execute shell commands (requires confirmation)",
                "\n--- RESPONSE FORMAT ---",
                "Format your response as JSON:",
                '{"thought": "your reasoning", "action": "describe what to do", "tool": "tool_name", "args": {...}}',
                "OR respond directly:",
                '{"response": "your direct answer"}',
            ]
        )

        # Add conversation history
        if self.conversation_history:
            prompt_parts.append("\n--- CONVERSATION HISTORY ---")
            for msg in self.conversation_history[-10:]:  # Last 10 messages
                role = msg["role"]
                content = msg["content"]
                prompt_parts.append(f"{role}: {content}")

        prompt_parts.append(f"\n--- CURRENT REQUEST ---\nUser: {user_query}")

        return "\n".join(prompt_parts)

    async def _execute_tool(self, tool: str, args: Dict[str, Any], call_id: str) -> str:
        """Execute a tool with async support"""
        self.display_manager.add_tool_call(call_id, {"tool": tool, "args": args})

        try:
            if tool == "read_file":
                path = args.get("path", "")
                result = read_file(path)
            elif tool == "write_file":
                path = args.get("path", "")
                content = args.get("content", "")
                result = write_file(path, content)
            elif tool == "list_files":
                result = list_files()
            elif tool == "run_command":
                command = args.get("command", "")
                # For run_command, we need confirmation
                self.console.print(
                    Panel(
                        f"[yellow]Command:[/yellow] [cyan]{command}[/cyan]",
                        title="⚠️ Safety Check",
                        border_style="yellow",
                        box=box.ROUNDED,
                    )
                )
                if not Prompt.ask("Allow execution?", default=False):
                    result = "Error: User denied command execution."
                else:
                    result = execute_command(command)
            else:
                result = f"Error: Unknown tool '{tool}'"

        except Exception as e:
            result = f"Error executing {tool}: {str(e)}"

        self.display_manager.complete_tool_call(call_id, result)
        return result

    async def _process_streaming_response(self, user_query: str) -> str:
        """Process streaming response from Ollama"""
        self.display_manager.start_display()

        try:
            prompt = self._build_prompt(user_query)

            # Use chat API with streaming
            response_stream = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat(
                    model="qwen2.5-coder:3b",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                ),
            )

            accumulated_response = ""
            current_call_id = None

            for chunk in response_stream:
                if self.is_cancelled:
                    break

                if "message" in chunk and "content" in chunk["message"]:
                    content = chunk["message"]["content"]
                    accumulated_response += content
                    self.display_manager.add_text(content)

                    # Try to detect and parse tool calls in streaming
                    # This is simplified - in real implementation would need proper JSON stream parsing
                    if '{"tool":' in accumulated_response:
                        # Found potential tool call, parse when complete
                        try:
                            tool_data = json.loads(accumulated_response)
                            if "tool" in tool_data:
                                call_id = str(uuid.uuid4())
                                tool_result = await self._execute_tool(
                                    tool_data["tool"],
                                    tool_data.get("args", {}),
                                    call_id,
                                )

                                # Continue with tool result in conversation
                                if "response" not in tool_data:
                                    followup_prompt = f"Tool result: {tool_result}"
                                    # Recursively handle followup...

                        except json.JSONDecodeError:
                            # Not complete JSON yet, continue accumulating
                            pass

        except Exception as e:
            self.console.print(f"❌ Error: {e}", style="red")

        finally:
            self.display_manager.stop_display()

        return accumulated_response

    async def process_message(self, user_query: str) -> str:
        """Process a user message with concurrency control"""
        async with self.semaphore:
            self._ensure_agent_initialized()

            # Add user message to history
            self.conversation_history.append(
                {"role": "user", "content": user_query, "timestamp": datetime.now()}
            )

            # Process response
            response = await self._process_streaming_response(user_query)

            # Add agent response to history
            self.conversation_history.append(
                {"role": "agent", "content": response, "timestamp": datetime.now()}
            )

            return response

    def cleanup(self):
        """Cleanup resources"""
        self.is_cancelled = True
        self.display_manager.stop_display()
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            self.keyboard_thread.join(timeout=1)


def main():
    """Main entry point for orangecode command"""
    try:
        # Display welcome banner
        console = Console()
        console.print(
            Panel(
                "[bold cyan]🍊 Orange Code - AI Coding Assistant[/bold cyan]\n\n"
                "[yellow]Commands:[/yellow]\n"
                "• Type your coding questions directly\n"
                "• [green]config[/green] - Show configuration\n" 
                "• [green]quit[/green]/[green]exit[/green] - Exit\n"
                "• [green]ESC[/green] - Cancel current operation\n\n"
                "[yellow]Example:[/yellow]\n"
                "  orangecode> Write a Python function for fibonacci\n"
                "  orangecode> Read main.py and add logging",
                title="🤖 Welcome",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        
        # Interactive loop
        scheduler = AgentScheduler()
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]orangecode[/bold green]")
                
                if user_input.lower() in ["quit", "exit"]:
                    console.print("[bold green]👋 Goodbye![/bold green]")
                    break
                    
                if user_input.lower() == "config":
                    # Show configuration
                    scheduler._ensure_agent_initialized()
                    ollama_host = os.getenv("OLLAMA_HOST", "http://10.0.0.55:11434")
                    console.print(
                        Panel(
                            f"[bold cyan]🍊 Orange Code Configuration[/bold cyan]\n\n"
                            f"Ollama Host: [green]{ollama_host}[/green]\n"
                            f"Model: [green]qwen2.5-coder:3b[/green]\n"
                            f"Project Context: [green]{scheduler.project_context[:100]}...[/green]" if len(scheduler.project_context) > 100 else f"Project Context: [green]{scheduler.project_context}[/green]",
                            title="⚙️ Config",
                            border_style="cyan",
                            box=box.ROUNDED,
                        )
                    )
                    continue
                    
                if user_input.strip():
                    # Process the user's query
                    asyncio.run(scheduler.process_message(user_input))
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use [bold]orangecode quit[/bold] to exit[/yellow]")
                continue
            except EOFError:
                console.print("[bold green]👋 Goodbye![/bold green]")
                break
                
    finally:
        if 'scheduler' in locals():
            scheduler.cleanup()


if __name__ == "__main__":
    main()
        scheduler.cleanup()


def main():
    """Main entry point for orangecode command"""
    cli_main()
