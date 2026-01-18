"""
Enhanced tool executor with automatic retry mechanism for LLM API calls
Handles rate limiting, timeouts, and service unavailability with intelligent backoff
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable, Type
from enum import Enum
import time

from llm_retry import (
    LLMErrorHandler, 
    LLMRetryConfig, 
    llm_retry, 
    create_retry_aware_client,
    LLMErrorType
    LLMError
)


class ToolExecutor:
    """Enhanced tool executor with LLM API retry mechanism"""
    
    def __init__(
        self,
        retry_client: Any,  # Could be agent_no_rag or direct LLM client
        retry_config: Optional[LLMRetryConfig] = None
        error_handler: Optional[LLMErrorHandler] = None
    ):
        self.retry_client = retry_client
        self.retry_config = retry_config or LLMRetryConfig()
        self.error_handler = error_handler or LLMErrorHandler()
        
        # Tool registry
        self.tool_registry = get_all_tools()
        
        # Statistics
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'retry_attempts': 0,
            'error_types': {}
        }
    
    def _execute_with_llm_planning(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        user_query: str
    ) -> str:
        """Execute tool using LLM to plan the execution"""
        try:
            # Create planning prompt for LLM
            planning_prompt = f"""
You are an expert programming assistant. I need to execute a tool call:

Tool: {tool_name}
Arguments: {tool_args}

Please provide a step-by-step plan to execute this tool safely and effectively.
Consider:
1. Safety checks and validation
2. Error handling and edge cases
3. Best practices for this type of operation
4. Any additional setup needed

Respond with a JSON plan in the format:
{{
    "plan": [
        {
            "step": "description of what to do",
            "validation": "what to check",
            "command": "command to execute"
        }
    ],
    "direct_command": "command if tool can be executed directly"
}}
"""
            
            # Get LLM client with retry
            from llm_retry import create_retry_aware_client
            llm_client = create_retry_aware_client(
                self.retry_client if hasattr(self.retry_client, 'chat') else None,
                config=self.retry_config
            )
            
            messages = [
                {"role": "system", "content": planning_prompt},
                {"role": "user", "content": user_query}
            ]
            
            # Get LLM plan
            response = await llm_client.chat_with_retry(
                model="qwen2.5-coder:3b",
                messages=messages
            )
            
            try:
                plan_data = json.loads(response["message"]["content"])
                
                if "plan" in plan_data:
                    for i, step in enumerate(plan_data["plan"], 1):
                        console.print(f"[blue]Step {i}: {step['step']}[/blue]")
                        if step.get("validation"):
                            console.print(f"[yellow]  Validation: {step['validation']}[/yellow]")
                        if step.get("command"):
                            console.print(f"[green]  Command: {step['command']}[/green]")
                
                if "direct_command" in plan_data:
                    # Execute direct command
                    command = plan_data["direct_command"]
                    return await self._execute_tool_safely(tool_name, {"command": command})
                
            except json.JSONDecodeError:
                console.print("[red]❌ Failed to parse LLM response[/red]")
                return "❌ Failed to parse LLM response"
                
        except Exception as e:
            console.print(f"[red]❌ LLM planning failed: {str(e)}[/red]")
            return f"❌ LLM planning failed: {str(e)}"
    
    async def _execute_with_llm_validation(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        code_content: str,
        user_query: str
    ) -> str:
        """Execute tool using LLM to validate and then execute"""
        try:
            # Create validation prompt for LLM
            validation_prompt = f"""
You are a code security expert. I need to validate this code before execution:

Code:
```{code_content}
```

User Request: {user_query}
Tool: {tool_name}

Please analyze:
1. Security vulnerabilities (SQL injection, code injection, path traversal)
2. Potential bugs or logic errors
3. Performance issues
4. Best practices violations
5. Compliance with coding standards

Respond with a JSON validation result in the format:
{{
    "is_safe": true/false,
    "issues": [
        {
            "severity": "low/medium/high/critical",
            "type": "security/performance/logic",
            "description": "detailed description of the issue",
            "line_number": "relevant line if applicable",
            "suggestion": "how to fix it"
        }
    ],
    "sanitized_code": "safe version of the code if needed"
}}
"""
            
            # Get LLM client with retry
            from llm_retry import create_retry_aware_client
            llm_client = create_retry_aware_client(
                self.retry_client if hasattr(self.retry_client, 'chat') else None,
                config=self.retry_config
            )
            
            messages = [
                {"role": "system", "content": validation_prompt},
                {"role": "user", "content": f"Please validate this code:\\n{code_content}\\nUser: {user_query}\\nTool: {tool_name}"}
            ]
            
            # Get LLM validation
            response = await llm_client.chat_with_retry(
                model="qwen2.5-coder:3b",
                messages=messages
            )
            
            try:
                validation_result = json.loads(response["message"]["content"])
                
                if validation_result.get("is_safe", False):
                    # Unsafe code detected
                    issues = validation_result.get("issues", [])
                    issue_descriptions = [f"❌ {issue.get('description', 'Unknown issue')}" for issue in issues]
                    console.print("[red]🚨 Code Validation Failed:[/red]")
                    for desc in issue_descriptions:
                        console.print(f"[red]  {desc}[/red]")
                    return f"❌ Code validation failed: {'; '.join(issue_descriptions)}"
                
                # If code needs sanitization
                if validation_result.get("sanitized_code"):
                    console.print("[yellow]📝 Code sanitized for safety[/yellow]")
                    return await self._execute_tool_safely(tool_name, {"sanitized_code": validation_result["sanitized_code"]})
                
                # Code is safe to execute
                console.print("[green]✅ Code validation passed[/green]")
                return await self._execute_tool_safely(tool_name, tool_args)
                
            except json.JSONDecodeError:
                console.print("[red]❌ Failed to parse validation response[/red]")
                return "❌ Failed to parse validation response"
                
        except Exception as e:
            console.print(f"[red]❌ LLM validation failed: {str(e)}[/red]")
            return f"❌ LLM validation failed: {str(e)}"
    
    async def _execute_tool_safely(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute tool with safety checks"""
        try:
            # Get tool function from registry
            from tools import get_all_tools
            tool_registry = get_all_tools()
            
            if tool_name not in tool_registry:
                return f"❌ Unknown tool: {tool_name}"
            
            tool_info = tool_registry[tool_name]
            tool_function = tool_info['function']
            
            console.print(f"[blue]🔧 Executing {tool_name} with args: {args}[/blue]")
            
            # Execute tool function
            result = tool_function(**args)
            
            self.execution_stats['total_executions'] += 1
            self.execution_stats['successful_executions'] += 1
            
            console.print(f"[green]✅ {tool_name} completed[/green]")
            return result
            
        except Exception as e:
            self.execution_stats['total_executions'] += 1
            self.execution_stats['failed_executions'] += 1
            console.print(f"[red]❌ {tool_name} failed: {str(e)}[/red]")
            return f"❌ {tool_name} failed: {str(e)}"
    
    async def execute_tool_with_retry(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_query: str
    ) -> str:
        """Execute tool with LLM planning and validation"""
        try:
            self.execution_stats['total_executions'] += 1
            
            # Step 1: LLM planning
            console.print(f"[blue]🤖 Planning {tool_name} execution...[/blue]")
            
            if tool_name in ["read_file", "write_file", "list_files"]:
                # Simple file operations can be executed directly
                return await self._execute_tool_safely(tool_name, tool_args)
            
            # Step 2: LLM validation for complex operations
            if tool_name in ["execute_shell"]:
                # For shell commands, we need validation
                return await self._execute_with_llm_validation(
                    tool_name, tool_args, 
                    user_query,
                    args.get("command", "")
                )
            
            # Step 3: LLM planning for any operation
            return await self._execute_with_llm_planning(
                tool_name, tool_args, user_query
            )
            
        except Exception as e:
            console.print(f"[red]❌ Tool execution failed: {str(e)}[/red]")
            self.execution_stats['failed_executions'] += 1
            return f"❌ Tool execution failed: {str(e)}"
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.execution_stats.copy()
    
    def reset_stats(self):
        """Reset execution statistics"""
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'retry_attempts': 0,
            'error_types': {}
        }


# Example usage in agent_no_rag.py:
"""
# Replace the basic _execute_tool method
async def _execute_tool(self, tool: str, args: Dict[str, Any], call_id: str) -> str:
    # Create enhanced tool executor
    tool_executor = ToolExecutor(self.retry_client)
    
    # Execute with retry mechanism
    result = await tool_executor.execute_tool_with_retry(tool, args, f"Execute {tool}")
    
    return result
"""