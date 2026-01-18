"""
LLM API Error Handling and Retry Mechanism
Provides robust error handling with exponential backoff and jitter for LLM API calls
"""

import asyncio
import random
import time
from typing import Optional, Callable, Any, Type
from enum import Enum
import logging
from functools import wraps
from rich.console import Console

# Setup logging
logger = logging.getLogger(__name__)
console = Console()


class LLMErrorType(Enum):
    """LLM API error types"""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    MODEL_NOT_FOUND = "model_not_found"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class LLMRetryConfig:
    """Configuration for LLM retry mechanism"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter_factor: float = 0.1,
        retryable_errors: Optional[list[LLMErrorType]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter_factor = jitter_factor

        # Default retryable errors
        if retryable_errors is None:
            self.retryable_errors = [
                LLMErrorType.RATE_LIMIT,
                LLMErrorType.TIMEOUT,
                LLMErrorType.SERVICE_UNAVAILABLE,
                LLMErrorType.NETWORK_ERROR,
                LLMErrorType.SERVER_ERROR,
            ]
        else:
            self.retryable_errors = retryable_errors


class LLMError(Exception):
    """Custom LLM API error with retry information"""

    def __init__(
        self,
        message: str,
        error_type: LLMErrorType = LLMErrorType.UNKNOWN_ERROR,
        original_error: Optional[Exception] = None,
        retry_count: int = 0,
        should_retry: bool = True,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error
        self.retry_count = retry_count
        self.should_retry = should_retry


class LLMErrorHandler:
    """Handles LLM API errors with intelligent retry logic"""

    def __init__(self, config: Optional[LLMRetryConfig] = None):
        self.config = config or LLMRetryConfig()
        self.retry_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retry_attempts": 0,
            "error_types": {},
        }

    def classify_error(self, error: Exception) -> LLMErrorType:
        """Classify the type of LLM error"""
        error_message = str(error).lower()

        if "rate limit" in error_message or "too many requests" in error_message:
            return LLMErrorType.RATE_LIMIT
        elif "timeout" in error_message or "timed out" in error_message:
            return LLMErrorType.TIMEOUT
        elif "service unavailable" in error_message or "503" in error_message:
            return LLMErrorType.SERVICE_UNAVAILABLE
        elif "connection" in error_message or "network" in error_message:
            return LLMErrorType.NETWORK_ERROR
        elif "unauthorized" in error_message or "401" in error_message:
            return LLMErrorType.AUTHENTICATION_ERROR
        elif "model not found" in error_message or "404" in error_message:
            return LLMErrorType.MODEL_NOT_FOUND
        elif "invalid request" in error_message or "400" in error_message:
            return LLMErrorType.INVALID_REQUEST
        elif "server error" in error_message or "500" in error_message:
            return LLMErrorType.SERVER_ERROR
        else:
            return LLMErrorType.UNKNOWN_ERROR

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base**retry_count)

        # Cap at maximum delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter_factor * random.random()
        delay += jitter

        return delay

    def should_retry(self, error: LLMError) -> bool:
        """Determine if the error should be retried"""
        # Check if we've exceeded max retries
        if error.retry_count >= self.config.max_retries:
            return False

        # Check if error type is retryable
        return error.error_type in self.config.retryable_errors

    def log_retry_attempt(self, error: LLMError, delay: float):
        """Log retry attempt with rich formatting"""
        self.retry_stats["retry_attempts"] += 1
        self.retry_stats["error_types"][error.error_type.value] = (
            self.retry_stats["error_types"].get(error.error_type.value, 0) + 1
        )

        console.print(
            f"[yellow]⚠️  LLM API Error (Attempt {error.retry_count + 1}/{self.config.max_retries})[/yellow]\n"
            f"[red]Error Type:[/red] {error.error_type.value}\n"
            f"[red]Message:[/red] {str(error)}\n"
            f"[blue]Retrying in {delay:.2f}s...[/blue]"
        )

        logger.warning(
            f"LLM API error (attempt {error.retry_count + 1}/{self.config.max_retries}): "
            f"{error.error_type.value} - {str(error)}. Retrying in {delay:.2f}s"
        )

    def log_final_failure(self, error: LLMError):
        """Log final failure after all retries exhausted"""
        self.retry_stats["failed_calls"] += 1

        console.print(
            f"[red]❌ LLM API Failed After {self.config.max_retries} Attempts[/red]\n"
            f"[red]Final Error:[/red] {error.error_type.value}\n"
            f"[red]Message:[/red] {str(error)}"
        )

        logger.error(
            f"LLM API failed after {self.config.max_retries} attempts: "
            f"{error.error_type.value} - {str(error)}"
        )

    def log_success(self):
        """Log successful API call"""
        self.retry_stats["successful_calls"] += 1

        if self.retry_stats["retry_attempts"] > 0:
            console.print(
                f"[green]✅ LLM API Success After {self.retry_stats['retry_attempts']} Retries[/green]"
            )

        logger.info("LLM API call successful")


def llm_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter_factor: float = 0.1,
    retryable_errors: Optional[list[LLMErrorType]] = None,
):
    """
    Decorator for LLM API calls with automatic retry mechanism

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter_factor: Factor for random jitter (0-1)
        retryable_errors: List of error types that should be retried
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = LLMRetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter_factor=jitter_factor,
                retryable_errors=retryable_errors,
            )

            handler = LLMErrorHandler(config)
            handler.retry_stats["total_calls"] += 1

            last_error = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    handler.log_success()
                    return result

                except Exception as e:
                    error_type = handler.classify_error(e)
                    llm_error = LLMError(
                        message=str(e),
                        error_type=error_type,
                        original_error=e,
                        retry_count=attempt,
                        should_retry=handler.should_retry(
                            LLMError(str(e), error_type, retry_count=attempt)
                        ),
                    )

                    if attempt < config.max_retries and llm_error.should_retry:
                        delay = handler.calculate_delay(attempt)
                        handler.log_retry_attempt(llm_error, delay)
                        await asyncio.sleep(delay)
                        last_error = llm_error
                        continue
                    else:
                        if attempt < config.max_retries:
                            handler.log_final_failure(llm_error)
                        else:
                            handler.retry_stats["failed_calls"] += 1
                            console.print(f"[red]❌ LLM API Failed: {str(e)}[/red]")
                        raise llm_error

            # This should not be reached, but just in case
            if last_error:
                raise last_error

        return wrapper

    return decorator


class LLMClientWithRetry:
    """Enhanced LLM client with built-in retry mechanism"""

    def __init__(self, client, config: Optional[LLMRetryConfig] = None):
        self.client = client
        self.config = config or LLMRetryConfig()
        self.handler = LLMErrorHandler(self.config)

    @llm_retry(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def chat(self, model: str, messages: list, **kwargs):
        """Chat with automatic retry mechanism"""
        try:
            response = self.client.chat(model=model, messages=messages, **kwargs)
            return response
        except Exception as e:
            # Let the decorator handle the retry logic
            raise

    @llm_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
    async def generate(self, model: str, prompt: str, **kwargs):
        """Generate text with automatic retry mechanism"""
        try:
            response = self.client.generate(model=model, prompt=prompt, **kwargs)
            return response
        except Exception as e:
            # Let the decorator handle the retry logic
            raise

    def get_stats(self) -> dict:
        """Get retry statistics"""
        total = self.handler.retry_stats["total_calls"]
        successful = self.handler.retry_stats["successful_calls"]
        failed = self.handler.retry_stats["failed_calls"]

        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "retry_attempts": self.handler.retry_stats["retry_attempts"],
            "error_types": self.handler.retry_stats["error_types"],
        }


# Example usage with ollama client
class EnhancedOllamaClient:
    """Enhanced Ollama client with retry mechanism"""

    def __init__(
        self,
        host: str = "http://10.0.0.55:11434",
        config: Optional[LLMRetryConfig] = None,
    ):
        import ollama

        self.client = ollama.Client(host=host)
        self.retry_client = LLMClientWithRetry(self.client, config)

    async def chat_with_retry(self, model: str, messages: list, **kwargs):
        """Chat with automatic retry"""
        return await self.retry_client.chat(model=model, messages=messages, **kwargs)

    def get_retry_stats(self) -> dict:
        """Get retry statistics"""
        return self.retry_client.get_stats()


# Utility function for creating retry-aware clients
def create_retry_aware_client(
    client_type: str = "ollama",
    host: str = "http://10.0.0.55:11434",
    config: Optional[LLMRetryConfig] = None,
):
    """Factory function to create retry-aware LLM clients"""

    if client_type.lower() == "ollama":
        return EnhancedOllamaClient(host=host, config=config)
    else:
        raise ValueError(f"Unsupported client type: {client_type}")


# Example usage in agent_no_rag.py
"""
# Replace the direct ollama client calls with retry-aware calls:

# Old way:
# response = client.chat(model="qwen2.5-coder:3b", messages=messages)

# New way:
# retry_client = create_retry_aware_client("ollama", "http://10.0.0.55:11434")
# response = await retry_client.chat_with_retry("qwen2.5-coder:3b", messages)
# stats = retry_client.get_retry_stats()
"""
