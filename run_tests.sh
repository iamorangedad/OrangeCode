#!/bin/bash
# Run Orange Code unit tests from the project root.

if [ ! -f "pytest.ini" ]; then
    echo "Run this script from the project root."
    exit 1
fi

RUN_ALL=false
RUN_TOOLS=false
RUN_LLM=false
RUN_AGENT=false
RUN_MCP=false
RUN_ENV=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all) RUN_ALL=true; shift ;;
        --tools) RUN_TOOLS=true; shift ;;
        --llm) RUN_LLM=true; shift ;;
        --agent) RUN_AGENT=true; shift ;;
        --mcp) RUN_MCP=true; shift ;;
        --env) RUN_ENV=true; shift ;;
        -h|--help)
            echo "Usage: run_tests.sh [--all|--tools|--llm|--agent|--mcp|--env]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$RUN_ALL" = false ] && [ "$RUN_TOOLS" = false ] && [ "$RUN_LLM" = false ] && [ "$RUN_AGENT" = false ] && [ "$RUN_MCP" = false ] && [ "$RUN_ENV" = false ]; then
    RUN_ALL=true
fi

if [ "$RUN_ALL" = true ]; then
    python3 tests/run_all_tests.py
    exit $?
fi

if [ "$RUN_TOOLS" = true ]; then
    python3 tests/test_tools.py
fi
if [ "$RUN_LLM" = true ]; then
    python3 tests/test_llm.py
fi
if [ "$RUN_AGENT" = true ]; then
    python3 tests/test_agent.py
fi
if [ "$RUN_MCP" = true ]; then
    python3 tests/test_mcp.py
fi
if [ "$RUN_ENV" = true ]; then
    python3 tests/test_environment.py
fi
