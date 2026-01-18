# Orange Code Unit Test Suite

## Overview

Comprehensive unit test suite covering all major functionality of the Orange Code AI coding assistant.

## Test Structure

```
tests/
├── pytest.ini                    # Pytest configuration
├── run_all_tests.py             # Main test runner
├── test_tools.py                # Tool system tests
├── test_retry.py                # Retry mechanism tests
├── test_tool_executor.py        # Tool executor tests
├── test_utils.py                # Utility function tests
├── test_environment.py           # Environment setup tests
└── README.md                    # Testing documentation
```

## Test Coverage

### 1. test_tools.py - Tool Registration & Permission Management

**Test Classes:**
- `TestPermissionLevel` - Permission level enumeration
- `TestSkillRestriction` - Skill restriction enumeration
- `TestFunctionTool` - @function_tool decorator
- `TestPermissionGuard` - Permission guard functionality
- `TestBuiltInTools` - Built-in tool verification
- `TestToolModels` - Pydantic model validation
- `TestRegisterSkillPermissions` - Skill registration

**Test Cases: 20+**
- ✅ Permission level values and count
- ✅ Skill restriction values and count
- ✅ Tool registration with metadata
- ✅ Automatic tool naming
- ✅ Skill restrictions on tools
- ✅ Permission check for allowed tools
- ✅ Permission check for restricted tools
- ✅ Restricted tools filtering
- ✅ Active skills registration
- ✅ All built-in tools verification
- ✅ Pydantic model validation

### 2. test_retry.py - LLM Retry Mechanism

**Test Classes:**
- `TestLLMErrorType` - Error type enumeration
- `TestLLMError` - Custom exception handling
- `TestLLMRetryConfig` - Configuration testing
- `TestLLMErrorHandler` - Error handler functionality
- `TestLLMRetryDecorator` - @llm_retry decorator
- `TestRetryAwareClient` - Client creation
- `TestRetryStatistics` - Statistics tracking

**Test Cases: 15+**
- ✅ Error type definitions
- ✅ LLM error creation and handling
- ✅ Default and custom configurations
- ✅ Error classification for different types
- ✅ Retry delay calculation with/without jitter
- ✅ Exponential backoff verification
- ✅ Successful call without retry
- ✅ Retry on timeout errors
- ✅ Max retries exceeded handling
- ✅ Rate limit retry testing
- ✅ Retry-aware client creation

### 3. test_tool_executor.py - Tool Execution Engine

**Test Classes:**
- `TestToolExecutorInitialization` - Executor setup
- `TestToolLoading` - Tool loading
- `TestToolExecution` - Tool execution
- `TestRequiresLLMRetry` - Retry detection
- `TestDirectExecution` - Direct execution path
- `TestListTools` - Tool listing
- `TestCleanup` - Resource cleanup
- `TestFileOperations` - File operations

**Test Cases: 12+**
- ✅ Default and custom initialization
- ✅ Tool loading verification
- ✅ Non-existent tool handling
- ✅ Tool execution with/without retry
- ✅ Timeout handling
- ✅ LLM retry requirement detection
- ✅ Direct execution success and error handling
- ✅ Tool listing with descriptions
- ✅ File operations via executor
- ✅ Read/write/list operations

### 4. test_utils.py - Utility Functions

**Test Classes:**
- `TestReadFile` - File reading
- `TestWriteFile` - File writing
- `TestListFiles` - Directory listing
- `TestExecuteCommand` - Command execution
- `TestExtractFilenameFromCode` - Code filename extraction
- `TestGetUniqueFilename` - Unique filename generation
- `TestUtilityFunctions` - Integration tests

**Test Cases: 20+**
- ✅ Reading existing and non-existent files
- ✅ File encoding handling
- ✅ Writing new and existing files
- ✅ Directory listing
- ✅ Successful command execution
- ✅ Command with stderr output
- ✅ Command timeout handling
- ✅ Invalid command handling
- ✅ Python class/function extraction
- ✅ Flask/FastAPI app detection
- ✅ React component extraction
- ✅ JavaScript server detection
- ✅ Bash script detection
- ✅ Cross-language pattern matching
- ✅ Unique filename generation
- ✅ Multiple counter increments

### 5. test_environment.py - Environment Setup

**Test Functions:**
- `test_dependencies` - Package installation verification
- `test_ollama_connection` - LLM service connectivity
- `test_agent_files` - Project file validation

**Test Cases: 3+**
- ✅ Required packages (ollama, rich, requests)
- ✅ Ollama service connection
- ✅ Project file existence

## Running Tests

### All Tests
```bash
# Run complete test suite
python3 tests/run_all_tests.py

# Or use pytest directly
pytest tests/ -v
```

### Individual Modules
```bash
# Test specific module
pytest tests/test_tools.py -v
pytest tests/test_retry.py -v
pytest tests/test_tool_executor.py -v
pytest tests/test_utils.py -v
pytest tests/test_environment.py -v
```

### Specific Tests
```bash
# Run specific test class
pytest tests/test_tools.py::TestPermissionLevel -v
pytest tests/test_retry.py::TestLLMRetryDecorator -v

# Run specific test method
pytest tests/test_tools.py::TestPermissionLevel::test_permission_level_values -v
```

## Test Framework

- **pytest**: Core testing framework
- **pytest-asyncio**: Async test support
- **unittest.mock**: Mocking and patching
- **tempfile**: Safe temporary file handling
- **subprocess**: Command execution testing

## Test Statistics

| Module | Test Classes | Test Cases | Lines of Code |
|---------|--------------|-------------|----------------|
| tools.py | 7 | 20+ | 231 |
| retry.py | 7 | 15+ | 217 |
| tool_executor.py | 8 | 12+ | 189 |
| utils.py | 7 | 20+ | 263 |
| environment.py | 3 | 3+ | 85 |
| **Total** | **32** | **70+** | **985** |

## Coverage Areas

### Core Functionality
- ✅ Tool registration and management
- ✅ Permission-based access control
- ✅ Skill restrictions and filtering
- ✅ LLM API retry mechanisms
- ✅ Error classification and handling
- ✅ Exponential backoff with jitter
- ✅ Tool execution with/without retry
- ✅ Timeout and error handling
- ✅ File operations (read/write/list)
- ✅ Command execution with safety
- ✅ Code pattern recognition
- ✅ Filename generation strategies

### Edge Cases
- ✅ Non-existent tools/files
- ✅ Timeout scenarios
- ✅ Max retry exceeded
- ✅ Rate limiting
- ✅ Invalid commands
- ✅ Encoding issues
- ✅ Concurrent file access

### Integration
- ✅ Tool executor ↔ Tools system
- ✅ Retry mechanism ↔ Tool execution
- ✅ Utils ↔ File operations
- ✅ Environment ↔ Dependencies

## Features

- **Async Support**: Full async/await testing
- **Mocking**: Isolated unit tests
- **Temp Files**: Safe file handling
- **Error Scenarios**: Comprehensive error testing
- **CI/CD Ready**: Exit codes for automation
- **Fast Execution**: Quick test runs
- **Clear Reporting**: Detailed test output

## Dependencies

```bash
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Continuous Integration

The test suite is designed for CI/CD:
- Exit code 0: All tests passed
- Exit code 1: Tests failed
- Compatible with GitHub Actions, GitLab CI, Jenkins

## Contributing

When adding new features:
1. Add corresponding unit tests
2. Follow existing test patterns
3. Use descriptive test names
4. Test both success and failure cases
5. Include edge case scenarios
6. Update this documentation

## Status

✅ **Production Ready**
- 70+ unit tests covering core functionality
- All major modules tested
- CI/CD compatible
- Comprehensive documentation
- Regular execution verified