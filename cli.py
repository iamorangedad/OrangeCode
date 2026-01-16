#!/usr/bin/env python3
"""
CLI entry point for No-RAG Agent with Scheduler
Usage: koder "your query here"
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent_no_rag import main as agent_main

if __name__ == "__main__":
    # Set up CLI interface like the design described
    if len(sys.argv) < 2:
        print("Usage: koder <query>")
        print("       koder config")
        sys.exit(1)

    # Pass arguments to agent
    sys.argv[0] = "koder"  # Update program name
    agent_main()
