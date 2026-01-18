# Orange Code Test Environment

## Quick Start

```bash
# Run all unit tests
python3 run_all_tests.py

# Run specific test module
python3 test_tools.py
python3 test_retry.py
python3 test_tool_executor.py
python3 test_utils.py

# Start Orange Code in test environment
./run.sh

# Or run directly
python3 orangecode.py
```

## Environment

- **Python**: 3.11+
- **Dependencies**: uv package manager
- **LLM**: Ollama with qwen2.5-coder:3b model
- **Test Framework**: pytest with asyncio support

## Configuration

Edit `.env` file to configure:

```
OLLAMA_HOST=http://10.0.0.55:11434
OLLAMA_MODEL=qwen2.5-coder:3b
```

## Test Coverage

### Unit Tests

The test suite includes comprehensive unit tests for all core modules:

1. **test_tools.py** - Tool Registration and Permission Management
   - Permission level enum testing
   - Skill restriction validation
   - Tool registration functionality
   - Permission guard operations
   - Built-in tools verification
   - Pydantic model validation

2. **test_retry.py** - LLM Retry Mechanism
   - Error type classification
   - LLM error handling
   - Retry configuration testing
   - Exponential backoff verification
   - Retry decorator functionality
   - Retry-aware client testing

3. **test_tool_executor.py** - Tool Execution Engine
   - Executor initialization
   - Tool loading and registration
   - Tool execution with/without retry
   - Timeout handling
   - File operations integration
   - Direct vs retry execution paths

4. **test_utils.py** - Utility Functions
   - File operations (read/write/list)
   - Command execution
   - Code filename extraction
   - Unique filename generation
   - Cross-language pattern matching

5. **test_environment.py** - Environment Setup
   - Dependency installation verification
   - Ollama connection testing
   - Project file validation

## Running Tests

### All Tests
```bash
python3 run_all_tests.py
```

### Individual Test Files
```bash
# Run with pytest
pytest test_tools.py -v
pytest test_retry.py -v
pytest test_tool_executor.py -v
pytest test_utils.py -v

# Run directly
python3 test_tools.py
python3 test_retry.py
python3 test_tool_executor.py
python3 test_utils.py
```

### Specific Test Classes
```bash
# Run specific test class
pytest test_tools.py::TestPermissionLevel -v
pytest test_retry.py::TestLLMErrorHandler -v
pytest test_utils.py::TestReadFile -v

# Run specific test method
pytest test_tools.py::TestPermissionLevel::test_permission_level_values -v
```

## Test Framework

The test suite uses:
- **pytest**: Core testing framework
- **pytest-asyncio**: Async test support
- **unittest.mock**: Mocking and patching

## Features

- **Comprehensive Coverage**: Tests for all major functionality
- **Async Support**: Full async/await testing capability
- **Mocking**: Isolated unit tests without external dependencies
- **File Operations**: Safe temp file handling
- **Error Scenarios**: Timeout and error condition testing

## Test Results

The test runner provides:
- Real-time test execution progress
- Detailed success/failure reporting
- Summary statistics
- Exit code for CI/CD integration

## Notes

- Make sure Ollama is running before integration tests
- Some tests may require network connectivity for external APIs
- The system will automatically load project context from AGENTS.md
- Tests are designed to be fast and repeatable