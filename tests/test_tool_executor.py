#!/usr/bin/env python3
"""
Unit tests for tool_executor.py - Tool execution engine
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from tool_executor import ToolExecutor
from retry import LLMRetryConfig


class TestToolExecutorInitialization:
    """Test ToolExecutor initialization"""

    def test_default_initialization(self):
        """Test default tool executor initialization"""
        executor = ToolExecutor()
        assert executor.retry_config is not None
        assert executor.error_handler is not None
        assert len(executor.tools) > 0

    def test_custom_config_initialization(self):
        """Test tool executor with custom config"""
        config = LLMRetryConfig(max_retries=5)
        executor = ToolExecutor(retry_config=config)
        assert executor.retry_config.max_retries == 5

    def test_retry_client_initialization(self):
        """Test tool executor with retry client"""
        mock_client = Mock()
        executor = ToolExecutor(retry_client=mock_client)
        assert executor.retry_client is not None


class TestToolLoading:
    """Test tool loading functionality"""

    def test_load_tools(self):
        """Test that tools are loaded correctly"""
        executor = ToolExecutor()
        assert len(executor.tools) > 0

    def test_read_file_tool_loaded(self):
        """Test that read_file tool is loaded"""
        executor = ToolExecutor()
        assert "read_file" in executor.tools

    def test_write_file_tool_loaded(self):
        """Test that write_file tool is loaded"""
        executor = ToolExecutor()
        assert "write_file" in executor.tools

    def test_execute_shell_tool_loaded(self):
        """Test that execute_shell tool is loaded"""
        executor = ToolExecutor()
        assert "execute_shell" in executor.tools


class TestToolExecution:
    """Test tool execution functionality"""

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool"""
        executor = ToolExecutor()
        result = await executor.execute_tool("nonexistent_tool", {})
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_without_retry(self):
        """Test executing tool without LLM retry"""
        executor = ToolExecutor()
        result = await executor.execute_tool("list_files", {"path": "."})
        assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test tool execution with timeout"""
        executor = ToolExecutor()
        result = await executor.execute_tool("list_files", {"path": "."}, timeout=5.0)
        assert "success" in result


class TestRequiresLLMRetry:
    """Test LLM retry detection"""

    def test_read_file_requires_no_retry(self):
        """Test that read_file doesn't require LLM retry"""
        executor = ToolExecutor()
        assert executor._requires_llm_retry("read_file") is False

    def test_write_file_requires_no_retry(self):
        """Test that write_file doesn't require LLM retry"""
        executor = ToolExecutor()
        assert executor._requires_llm_retry("write_file") is False

    def test_generate_code_requires_retry(self):
        """Test that generate_code requires LLM retry"""
        executor = ToolExecutor()
        assert executor._requires_llm_retry("generate_code") is True


class TestDirectExecution:
    """Test direct tool execution without retry"""

    @pytest.mark.asyncio
    async def test_direct_execution_success(self):
        """Test successful direct execution"""
        executor = ToolExecutor()
        result = await executor._execute_direct(
            executor.tools["list_files"], {"path": "."}, None
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_direct_execution_timeout(self):
        """Test direct execution timeout"""

        async def slow_tool():
            await asyncio.sleep(5.0)
            return "result"

        executor = ToolExecutor()
        result = await executor._execute_direct(slow_tool, {}, 0.1)
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_direct_execution_error(self):
        """Test direct execution with error"""

        async def failing_tool():
            raise ValueError("Test error")

        executor = ToolExecutor()
        result = await executor._execute_direct(failing_tool, {}, None)
        assert result["success"] is False
        assert "failed" in result["error"].lower()


class TestListTools:
    """Test tool listing functionality"""

    def test_list_tools(self):
        """Test listing all tools"""
        executor = ToolExecutor()
        tools = executor.list_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_list_tools_descriptions(self):
        """Test that tool descriptions are available"""
        executor = ToolExecutor()
        tools = executor.list_tools()

        for tool_name, tool_info in tools.items():
            assert "description" in tool_info
            assert "requires_retry" in tool_info

    def test_list_tools_read_file_info(self):
        """Test read_file tool info"""
        executor = ToolExecutor()
        tools = executor.list_tools()

        if "read_file" in tools:
            assert tools["read_file"]["requires_retry"] is False


class TestCleanup:
    """Test cleanup functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test cleanup method"""
        executor = ToolExecutor()
        await executor.cleanup()
        assert True  # Cleanup should complete without errors


class TestFileOperations:
    """Test file operations through tool executor"""

    @pytest.mark.asyncio
    async def test_read_file_via_executor(self):
        """Test reading file via executor"""
        executor = ToolExecutor()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_file = f.name

        try:
            result = await executor.execute_tool("read_file", {"path": temp_file})
            assert result["success"] is True
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_write_file_via_executor(self):
        """Test writing file via executor"""
        executor = ToolExecutor()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            result = await executor.execute_tool(
                "write_file", {"path": temp_file, "content": "test content"}
            )
            assert result["success"] is True

            with open(temp_file, "r") as f:
                content = f.read()
                assert content == "test content"
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_list_files_via_executor(self):
        """Test listing files via executor"""
        executor = ToolExecutor()
        result = await executor.execute_tool("list_files", {"path": "."})
        assert result["success"] is True


def run_all_tests():
    """Run all tests"""
    print("🧪 Running Tool Executor Tests")
    print("=" * 50)

    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_all_tests()
