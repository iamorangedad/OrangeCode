#!/usr/bin/env python3
"""
Enhanced tool executor with automatic retry mechanism for LLM API calls
Handles rate limiting, timeouts, and service unavailability with intelligent backoff
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable, Type
from enum import Enum
import time

from retry import (
    LLMErrorHandler,
    LLMRetryConfig,
    llm_retry,
    create_retry_aware_client,
    LLMErrorType,
    LLMError,
)


class ToolExecutor:
    """Enhanced tool executor with LLM API retry mechanism"""

    def __init__(
        self, retry_client=None, retry_config: Optional[LLMRetryConfig] = None
    ):
        """
        Initialize tool executor with retry mechanism

        Args:
            retry_client: Enhanced LLM client with retry capabilities
            retry_config: Retry configuration settings
        """
        self.retry_client = retry_client

        # Default retry configuration
        if retry_config is None:
            self.retry_config = LLMRetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter_factor=0.1,
            )
        else:
            self.retry_config = retry_config

        # Initialize error handler
        self.error_handler = LLMErrorHandler(self.retry_config)

        # Load tools
        self._load_tools()

    def _load_tools(self):
        """Load all available tools"""
        try:
            from tools import get_all_tools

            self.tools = get_all_tools()
        except ImportError:
            # Fallback if tools module not available
            self.tools = []

    async def execute_tool(
        self, tool_name: str, args: Dict[str, Any], timeout: Optional[float] = 30.0
    ) -> Dict[str, Any]:
        """
        Execute a tool with automatic retry mechanism

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
            timeout: Execution timeout in seconds

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        tool = self.tools[tool_name]

        # Check if tool requires retry mechanism (LLM-dependent operations)
        if self._requires_llm_retry(tool_name):
            return await self._execute_with_retry(tool, args, timeout)
        else:
            return await self._execute_direct(tool, args, timeout)

    def _requires_llm_retry(self, tool_name: str) -> bool:
        """Check if tool requires LLM retry mechanism"""
        retry_tools = {
            "generate_code",
            "analyze_code",
            "explain_code",
            "optimize_code",
            "refactor_code",
            "debug_code",
        }
        return tool_name in retry_tools

    async def _execute_with_retry(
        self, tool: Callable, args: Dict[str, Any], timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute tool with retry mechanism"""
        try:
            # Use retry decorator for LLM-dependent operations
            result = await llm_retry(
                tool,
                max_retries=self.retry_config.max_retries,
                base_delay=self.retry_config.base_delay,
                max_delay=self.retry_config.max_delay,
                exponential_base=self.retry_config.exponential_base,
                jitter_factor=self.retry_config.jitter_factor,
                timeout=timeout,
            )(**args)

            return {"success": True, "result": result}

        except LLMError as e:
            return {
                "success": False,
                "error": f"LLM operation failed after retries: {e}",
                "error_type": e.error_type,
                "retries_attempted": e.retries_attempted,
            }
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {e}"}

    async def _execute_direct(
        self, tool: Callable, args: Dict[str, Any], timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute tool directly without retry"""
        try:
            if timeout:
                result = await asyncio.wait_for(tool(**args), timeout=timeout)
            else:
                result = await tool(**args)

            return {"success": True, "result": result}

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Tool execution timed out after {timeout} seconds",
            }
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {e}"}

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their descriptions"""
        tool_info = {}
        for name, tool in self.tools.items():
            tool_info[name] = {
                "description": getattr(tool, "__doc__", "No description"),
                "requires_retry": self._requires_llm_retry(name),
            }
        return tool_info

    async def cleanup(self):
        """Clean up resources"""
        # Add any cleanup logic here
        pass


# Example usage
if __name__ == "__main__":

    async def test_tool_executor():
        executor = ToolExecutor()

        # Test listing tools
        tools = executor.list_tools()
        print(f"Available tools: {list(tools.keys())}")

        # Test tool execution
        result = await executor.execute_tool(
            "read_file", {"file_path": "/tmp/test.txt"}
        )
        print(f"Execution result: {result}")

    asyncio.run(test_tool_executor())
