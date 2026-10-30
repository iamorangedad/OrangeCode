#!/usr/bin/env python3
"""Command-line entry point for the Orange Code agent."""

from __future__ import annotations

import argparse
import sys

from agent import Agent
from session import latest_session, load_session, resolve_session


def main(argv: list[str] | None = None) -> int:
    """Run one request or start an interactive session."""
    parser = argparse.ArgumentParser(description="Orange Code, a minimal coding agent")
    parser.add_argument("query", nargs="*", help="Run one request and exit")
    parser.add_argument("--config", action="store_true", help="Print model and tool settings")
    parser.add_argument("--resume", metavar="ID", help="Continue a saved session")
    args = parser.parse_args(argv)

    agent = Agent.from_env(interactive=not args.query)
    try:
        if args.resume:
            loaded = restore_session(agent, args.resume)
            if loaded is None:
                return 1
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
    print("Type a request. Commands: config, resume, quit")
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
        if lowered == "resume":
            if not resume_latest(agent):
                print("No saved session.")
            continue
        try:
            print(agent.run(user_input))
        except KeyboardInterrupt:
            print("\nInterrupted.")


def restore_session(agent: Agent, session_id: str) -> list | None:
    """Load a saved transcript onto the agent. Return None when it is missing."""
    path = resolve_session(agent.registry.workspace, session_id)
    if not path.is_file():
        print(f"Session not found: {session_id}", file=sys.stderr)
        return None
    agent.messages = load_session(path)
    agent.session_path = path
    return agent.messages


def resume_latest(agent: Agent) -> bool:
    """Switch the agent to the newest saved session."""
    path = latest_session(agent.registry.workspace)
    if path is None:
        return False
    agent.messages = load_session(path)
    agent.session_path = path
    print(f"Resumed {path.stem}")
    return True


def print_config(agent: Agent) -> None:
    """Show the active model endpoint and tool names. The API key is omitted."""
    print(f"Model: {agent.llm.model}")
    print(f"Base URL: {agent.llm.base_url}")
    print(f"Workspace: {agent.registry.workspace}")
    print(f"Max steps: {agent.max_steps}")
    print(f"Shell: {agent.registry.shell_policy}")
    print(f"Check: {agent.check_command or '(none)'}")
    print("Tools: " + ", ".join(agent.tool_names()))


if __name__ == "__main__":
    sys.exit(main())
