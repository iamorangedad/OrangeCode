#!/usr/bin/env python3
"""
Orange Code CLI - Interactive AI Coding Assistant
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point for orangecode command"""
    try:
        # Display welcome banner
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
        from rich import box
        from agent_no_rag import AgentScheduler
        import asyncio
        
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
    except Exception as e:
        print(f"Error starting Orange Code: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()