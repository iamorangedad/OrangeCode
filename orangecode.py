#!/usr/bin/env python3
"""
Orange Code - AI Coding Assistant
Main entry point for the Orange Code application.
Simplified version without rich dependencies for testing.
"""

import os
import sys
import asyncio


def get_user_preference():
    """Get user preference for agent skill."""
    print("Choose your agent skill:")
    print("1. developer - For coding and development tasks")
    print("2. analyst - For code analysis and review")
    print("3. system - For system administration")
    print("4. general - For general assistance")

    while True:
        choice = input("Enter your choice (1-4, default=4): ").strip()
        if not choice:
            return "general"
        elif choice == "1":
            return "developer"
        elif choice == "2":
            return "analyst"
        elif choice == "3":
            return "system"
        elif choice == "4":
            return "general"
        else:
            print("Invalid choice. Please enter 1-4.")


def create_scheduler(skill):
    """Create scheduler with specified skill."""
    try:
        from agent import OrangeCodeScheduler

        scheduler = OrangeCodeScheduler(skill=skill)
        return scheduler
    except ImportError as e:
        print(f"Error importing scheduler: {e}")
        return None


def show_config(scheduler):
    """Show configuration."""
    if scheduler and hasattr(scheduler, "_ensure_agent_initialized"):
        try:
            scheduler._ensure_agent_initialized()
            ollama_host = os.getenv("OLLAMA_HOST", "http://10.0.0.55:11434")

            print("\n=== Orange Code Configuration ===")
            print(f"Ollama Host: {ollama_host}")
            print(f"Model: qwen2.5-coder:3b")
            if hasattr(scheduler, "project_context"):
                context = scheduler.project_context
                if len(context) > 100:
                    print(f"Project Context: {context[:100]}...")
                else:
                    print(f"Project Context: {context}")
            print("===============================\n")
        except Exception as e:
            print(f"Error showing config: {e}")
    else:
        print("Scheduler not available")


def main():
    """Main entry point."""
    try:
        print("🍊 Orange Code - AI Coding Assistant")
        print("Powered by local LLM with advanced scheduling")
        print()

        # Get user preference for skill
        user_skill = get_user_preference()

        # Create scheduler
        scheduler = create_scheduler(user_skill)

        if not scheduler:
            print("❌ Failed to initialize scheduler. Exiting.")
            return

        print(f"🎯 Orange Code Agent with skill '{user_skill}' is ready!")
        if scheduler and hasattr(scheduler, "get_tool_executor"):
            print(f"🛠️  Tools available: {len(scheduler.get_tool_executor().tools)}")
        print("💬 Type 'quit' to exit, 'config' to see configuration")
        print()

        # Main interaction loop
        while True:
            try:
                user_input = input("🤖 You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("👋 Goodbye!")
                    break

                if user_input.lower() == "config":
                    show_config(scheduler)
                    continue

                if user_input.strip():
                    # Process the user's query
                    print("🤖 Thinking...")
                    try:
                        if scheduler and hasattr(scheduler, "process_message"):
                            response = asyncio.run(
                                scheduler.process_message(user_input)
                            )
                            print(f"🤖 Orange: {response}")
                        else:
                            print("❌ Scheduler not available for processing")
                    except Exception as e:
                        print(f"❌ Error processing message: {e}")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except EOFError:
                print("\n👋 Goodbye!")
                break

    finally:
        if "scheduler" in locals() and scheduler:
            try:
                scheduler.cleanup()
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error starting Orange Code: {e}")
        sys.exit(1)
