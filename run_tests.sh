#!/bin/bash
# Quick test runner for Orange Code

echo "🧪 Orange Code - Quick Test Runner"
echo "=" * 50
echo ""

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    echo "❌ Error: Must run from project root directory"
    echo "   Please cd to the Orange Code directory"
    exit 1
fi

# Parse command line arguments
RUN_ALL=false
RUN_TOOLS=false
RUN_RETRY=false
RUN_EXECUTOR=false
RUN_UTILS=false
RUN_ENV=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_ALL=true
            shift
            ;;
        --tools)
            RUN_TOOLS=true
            shift
            ;;
        --retry)
            RUN_RETRY=true
            shift
            ;;
        --executor)
            RUN_EXECUTOR=true
            shift
            ;;
        --utils)
            RUN_UTILS=true
            shift
            ;;
        --env)
            RUN_ENV=true
            shift
            ;;
        -h|--help)
            echo "Usage: run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  --all       Run all tests (default)"
            echo "  --tools     Run tool registration tests"
            echo "  --retry     Run retry mechanism tests"
            echo "  --executor  Run tool executor tests"
            echo "  --utils     Run utility function tests"
            echo "  --env       Run environment setup tests"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "   Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# If no options specified, run all tests
if [ "$RUN_ALL" = false ] && [ "$RUN_TOOLS" = false ] && [ "$RUN_RETRY" = false ] && [ "$RUN_EXECUTOR" = false ] && [ "$RUN_UTILS" = false ] && [ "$RUN_ENV" = false ]; then
    RUN_ALL=true
fi

# Run tests based on selection
if [ "$RUN_ALL" = true ]; then
    echo "🚀 Running all tests..."
    python3 tests/run_all_tests.py
    exit $?
fi

if [ "$RUN_TOOLS" = true ]; then
    echo "🧪 Running tool registration tests..."
    python3 tests/test_tools.py
fi

if [ "$RUN_RETRY" = true ]; then
    echo "🧪 Running retry mechanism tests..."
    python3 tests/test_retry.py
fi

if [ "$RUN_EXECUTOR" = true ]; then
    echo "🧪 Running tool executor tests..."
    python3 tests/test_tool_executor.py
fi

if [ "$RUN_UTILS" = true ]; then
    echo "🧪 Running utility function tests..."
    python3 tests/test_utils.py
fi

if [ "$RUN_ENV" = true ]; then
    echo "🧪 Running environment setup tests..."
    python3 tests/test_environment.py
fi