#!/usr/bin/env python3
"""Command-line entry point for the Orange Code agent."""

from __future__ import annotations

import argparse
import sys

from agent import Agent


def main(argv: list[str] | None = None) -> int:
    """Run one request or start an interactive session."""
    parser = argparse.ArgumentParser(description="Orange Code, a minimal coding agent")
    parser.add_argument("query", nargs="*", help="Run one request and exit")
    parser.add_argument("--config", action="store_true", help="Print model and tool settings")
    args = parser.parse_args(argv)

    agent = Agent.from_env(interactive=not args.query)
    try:
        if args.config:
            print_config(agent)
            return 0
        if args.query:
            print(agent.run(" ".join(args.query)))
            return 0
        return interactive(agent)
    finally:
        agent.close()


def interactive(agent: Agent) -> int:
    """Read requests from the terminal until the user quits."""
    print("Orange Code")
    print("Type a request. Commands: config, quit")
    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        if not user_input:
            continue
        lowered = user_input.lower()
        if lowered in {"quit", "exit", "q"}:
            return 0
        if lowered == "config":
            print_config(agent)
            continue
        try:
            print(agent.run(user_input))
        except KeyboardInterrupt:
            print("\nInterrupted.")


def print_config(agent: Agent) -> None:
    """Show the active model endpoint and tool names. The API key is omitted."""
    print(f"Model: {agent.llm.model}")
    print(f"Base URL: {agent.llm.base_url}")
    print(f"Workspace: {agent.registry.workspace}")
    print(f"Max steps: {agent.max_steps}")
    print(f"Shell: {agent.registry.shell_policy}")
    print("Tools: " + ", ".join(agent.tool_names()))


if __name__ == "__main__":
    sys.exit(main())
