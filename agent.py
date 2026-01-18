#!/usr/bin/env python3
"""
AI Agent with advanced functionality

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
import uuid
import asyncio
import select
import signal
import argparse
import inspect
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
from tools import get_all_tools, register_skill_permissions
from retry import create_retry_aware_client, LLMRetryConfig


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


class OrangeCodeScheduler:
    """Main scheduler with lazy loading and concurrency control"""

    def __init__(self, skill: str = "general", active_skills: List[str] = None):
        if active_skills is None:
            active_skills = [f"{skill}_assistant"]
        self.console = Console()
        self.client: Optional[ollama.Client] = None
        self.retry_client = None  # Enhanced client with retry mechanism
        self.conversation_history: List[Dict[str, Any]] = []
        self.project_context: str = ""
        self.semaphore = asyncio.Semaphore(10)
        self.display_manager = StreamingDisplayManager(self.console)
        self.is_cancelled = False
        self.keyboard_thread: Optional[threading.Thread] = None

        # Lazy loading flag
        self._agent_initialized = False

        # Store skill for later use
        self.skill_name = skill

        # Retry configuration
        self.retry_config = LLMRetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter_factor=0.1,
        )

        # Tool permission management
        self.active_skills = active_skills
        self.permission_guard = register_skill_permissions(self.active_skills)

        # Create tool executor
        self._tool_executor = None
        self.available_tools = self.permission_guard.get_restricted_tools()

    def get_tool_executor(self):
        """Get the tool executor instance"""
        if self._tool_executor is None:
            from tool_executor import ToolExecutor

            self._tool_executor = ToolExecutor(self.retry_client)
        return self._tool_executor

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
        # 构建工具描述
        tool_descriptions = []
        for tool_name in self.available_tools:
            tool_info = get_all_tools()[tool_name]
            tool_descriptions.append(f"- {tool_name}: {tool_info['description']}")

        # 添加权限说明
        permission_info = f"""
--- PERMISSIONS ---
Active Skills: {", ".join(self.active_skills)}
Available Tools: {", ".join(self.available_tools)}
Note: Tools are filtered by active skill permissions.
"""

        prompt_parts = [
            "You are an autonomous coding agent with advanced tool management.",
        ]

        # Add project context if available
        if self.project_context:
            prompt_parts.append("\n--- PROJECT CONTEXT ---")
            prompt_parts.append(self.project_context)

        prompt_parts.extend(
            [
                "\n--- TOOLS AVAILABLE ---",
            ]
            + tool_descriptions
            + [
                permission_info,
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
        """Execute a tool with async support using LLM retry mechanism"""
        # Check tool permissions
        if not self.permission_guard.can_use_tool(tool):
            error_msg = (
                f"❌ 权限不足：当前技能 '{self.active_skills}' 不允许使用工具 '{tool}'"
            )
            self.display_manager.add_tool_call(call_id, {"tool": tool, "args": args})
            self.display_manager.complete_tool_call(call_id, error_msg)
            return error_msg

        # Use enhanced tool executor for complex operations
        from tool_executor import ToolExecutor

        # Create enhanced tool executor with retry mechanism
        tool_executor = ToolExecutor(self.retry_client)

        # For complex or risky operations, use LLM planning and validation
        if tool in ["execute_shell"]:
            return await tool_executor.execute_tool_with_llm_validation(
                tool, args, args.get("command", "")
            )

        # For other operations, use LLM planning
        elif tool in ["read_file", "write_file", "list_files"]:
            return await tool_executor.execute_tool_with_llm_planning(
                tool, args, user_query
            )

        # For simple operations, execute directly with retry
        else:
            return await tool_executor.execute_tool_with_retry(tool_name, args)

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
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Orange Code - AI Coding Assistant with Tool Management"
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        help="Active skills (e.g., --skills file_manager developer_assistant)",
    )
    parser.add_argument(
        "--list-tools", action="store_true", help="List all available tools"
    )
    parser.add_argument(
        "--list-skills", action="store_true", help="List all available skills"
    )

    # 解析已知参数
    known_args, remaining_args = parser.parse_known_args()

    try:
        # Display welcome banner
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
        from rich import box
        from rich.table import Table
        import asyncio

        console = Console()

        # 处理特殊命令
        if known_args.list_tools:
            _list_all_tools(console)
            return

        if known_args.list_skills:
            _list_all_skills(console)
            return

        # 设置活跃技能和重试配置
        active_skills = known_args.skills or ["developer_assistant"]

        # Initialize with retry mechanism
        # These will be set when AgentScheduler is created

        # 设置活跃技能
        active_skills = known_args.skills or ["developer_assistant"]

        console.print(
            Panel(
                f"[bold cyan]🍊 Orange Code - AI Coding Assistant[/bold cyan]\n\n"
                f"[yellow]Active Skills:[/yellow] [green]{', '.join(active_skills)}[/green]\n"
                "[yellow]Commands:[/yellow]\n"
                "• Type your coding questions directly\n"
                "• [green]config[/green] - Show configuration\n"
                "• [green]tools[/green] - List available tools\n"
                "• [green]quit[/green]/[green]exit[/green] - Exit\n"
                "• [green]ESC[/green] - Cancel current operation\n\n"
                "[yellow]Example:[/yellow]\n"
                "  orangecode> Write a Python function for fibonacci\n"
                "  orangecode> Read main.py and add logging\n"
                "  orangecode --skills file_manager --list-tools",
                title="🤖 Welcome",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

        # Interactive loop
        scheduler = AgentScheduler(active_skills=active_skills)

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
                    available_tools = ", ".join(scheduler.available_tools)
                    retry_stats = (
                        scheduler.retry_client.get_stats()
                        if hasattr(scheduler, "retry_client")
                        else {}
                    )
                    # Format project context based on length
                    project_context_display = (
                        f"Project Context: [green]{scheduler.project_context[:100]}...[/green]\n"
                        if len(scheduler.project_context) > 100
                        else f"Project Context: [green]{scheduler.project_context}[/green]\n"
                    )

                    console.print(
                        Panel(
                            f"[bold cyan]🍊 Orange Code Configuration[/bold cyan]\n\n"
                            f"Ollama Host: [green]{ollama_host}[/green]\n"
                            f"Model: [green]qwen2.5-coder:3b[/green]\n"
                            f"Active Skills: [green]{', '.join(scheduler.active_skills)}[/green]\n"
                            f"Available Tools: [green]{available_tools}[/green]\n"
                            f"{project_context_display}"
                            f"[yellow]Retry Stats:[/yellow] Total: {retry_stats.get('total_calls', 0)}, Success: {retry_stats.get('successful_calls', 0)}[/green]",
                            title="⚙️ Config",
                            border_style="cyan",
                            box=box.ROUNDED,
                        )
                    )
                    continue

                if user_input.lower() == "tools":
                    # Show available tools
                    _show_available_tools(console, scheduler)
                    continue

                if user_input.strip():
                    # Process the user's query
                    asyncio.run(scheduler.process_message(user_input))

            except KeyboardInterrupt:
                console.print(
                    "\n[yellow]Use [bold]orangecode quit[/bold] to exit[/yellow]"
                )
                continue
            except EOFError:
                console.print("[bold green]👋 Goodbye![/bold green]")
                break

    except Exception as e:
        print(f"Error starting Orange Code: {e}")
        sys.exit(1)
    finally:
        if "scheduler" in locals():
            scheduler.cleanup()


def _list_all_tools(console: Console):
    """列出所有注册的工具"""
    from rich.table import Table

    tools = get_all_tools()

    table = Table(title="🛠️ All Registered Tools")
    table.add_column("Tool Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Permissions", style="yellow")
    table.add_column("Skills", style="magenta")

    for tool_name, tool_info in tools.items():
        permissions = ", ".join([p.value for p in tool_info["permissions"]])
        skills = ", ".join([s.value for s in tool_info["skill_types"]])
        table.add_row(tool_name, tool_info["description"], permissions, skills)

    console.print(table)


def _list_all_skills(console: Console):
    """列出所有可用的技能"""
    from rich.table import Table

    table = Table(title="🎯 Available Skills")
    table.add_column("Skill Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Default Permissions", style="yellow")

    skills = {
        "file_manager": "File management operations (read, write, list)",
        "code_analyzer": "Code analysis and inspection (read-only)",
        "system_info": "System information gathering",
        "developer_assistant": "Full development assistant with all capabilities",
    }

    for skill, desc in skills.items():
        table.add_row(skill, desc, "Varies by skill type")

    console.print(table)


def _show_available_tools(console: Console, scheduler):
    """显示当前可用的工具和重试统计"""
    from rich.table import Table

    # Tools table
    tools_table = Table(
        title=f"🛠️ Available Tools (Skills: {', '.join(scheduler.active_skills)})"
    )
    tools_table.add_column("Tool Name", style="cyan")
    tools_table.add_column("Description", style="green")
    tools_table.add_column("Type", style="blue")

    for tool_name in scheduler.available_tools:
        tool_info = get_all_tools()[tool_name]
        tools_table.add_row(
            tool_name,
            tool_info["description"],
            tool_info.get("permissions", [])[0].value,
        )

    console.print(tools_table)

    # Retry statistics table
    retry_stats = (
        scheduler.retry_client.get_stats() if hasattr(scheduler, "retry_client") else {}
    )

    retry_table = Table(title=f"📊 Retry Statistics")
    retry_table.add_column("Metric", style="cyan")
    retry_table.add_column("Value", style="green")
    retry_table.add_row("Total Calls", f"{retry_stats.get('total_calls', 0)}")
    retry_table.add_row(
        "Success Rate",
        f"{retry_stats.get('successful_calls', 0) if retry_stats.get('total_calls', 0) else 0:.1%}",
    )
    retry_table.add_row("Failed Calls", f"{retry_stats.get('failed_calls', 0)}")

    console.print(retry_table)

    # Display retry configuration
    config_table = Table(title="⚙️ Retry Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_row("Max Retries", f"{scheduler.retry_config.max_retries}")
    config_table.add_row("Base Delay", f"{scheduler.retry_config.base_delay}s")
    config_table.add_row("Max Delay", f"{scheduler.retry_config.max_delay}s")
    config_table.add_row(
        "Exponential Base", f"{scheduler.retry_config.exponential_base}"
    )
    config_table.add_row("Jitter Factor", f"{scheduler.retry_config.jitter_factor}")

    console.print(config_table)


if __name__ == "__main__":
    main()
