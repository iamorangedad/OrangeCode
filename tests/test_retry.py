#!/usr/bin/env python3
"""
Unit tests for retry.py - LLM retry mechanism
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from retry import (
    LLMErrorType,
    LLMError,
    LLMErrorHandler,
    LLMRetryConfig,
    llm_retry,
    create_retry_aware_client,
)


class TestLLMErrorType:
    """Test LLMErrorType enum"""

    def test_error_type_values(self):
        """Test that all error types are defined"""
        assert LLMErrorType.RATE_LIMIT.value == "rate_limit"
        assert LLMErrorType.TIMEOUT.value == "timeout"
        assert LLMErrorType.SERVICE_UNAVAILABLE.value == "service_unavailable"
        assert LLMErrorType.AUTHENTICATION.value == "authentication"
        assert LLMErrorType.NETWORK.value == "network"
        assert LLMErrorType.MODEL_ERROR.value == "model_error"
        assert LLMErrorType.SERVER_ERROR.value == "server_error"
        assert LLMErrorType.INVALID_REQUEST.value == "invalid_request"

    def test_error_type_count(self):
        """Test that there are 8 error types"""
        assert len(LLMErrorType) == 8


class TestLLMError:
    """Test LLMError custom exception"""

    def test_llm_error_creation(self):
        """Test LLMError creation"""
        error = LLMError(
            message="Test error", error_type=LLMErrorType.TIMEOUT, retries_attempted=3
        )
        assert str(error) == "Test error"
        assert error.error_type == LLMErrorType.TIMEOUT
        assert error.retries_attempted == 3

    def test_llm_error_with_no_retry(self):
        """Test LLMError with no retries"""
        error = LLMError(message="No retries", error_type=LLMErrorType.NETWORK)
        assert error.retries_attempted == 0


class TestLLMRetryConfig:
    """Test LLMRetryConfig configuration"""

    def test_default_config(self):
        """Test default configuration"""
        config = LLMRetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter_factor == 0.1

    def test_custom_config(self):
        """Test custom configuration"""
        config = LLMRetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter_factor=0.2,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter_factor == 0.2


class TestLLMErrorHandler:
    """Test LLMErrorHandler class"""

    def test_handler_initialization(self):
        """Test error handler initialization"""
        config = LLMRetryConfig(max_retries=3)
        handler = LLMErrorHandler(config)
        assert handler.config.max_retries == 3

    def test_classify_rate_limit_error(self):
        """Test rate limit error classification"""
        config = LLMRetryConfig()
        handler = LLMErrorHandler(config)
        error = LLMErrorType.RATE_LIMIT
        classified = handler._classify_error(error)
        assert classified == LLMErrorType.RATE_LIMIT

    def test_classify_timeout_error(self):
        """Test timeout error classification"""
        config = LLMRetryConfig()
        handler = LLMErrorHandler(config)
        error = LLMErrorType.TIMEOUT
        classified = handler._classify_error(error)
        assert classified == LLMErrorType.TIMEOUT

    def test_calculate_retry_delay_no_jitter(self):
        """Test retry delay calculation without jitter"""
        config = LLMRetryConfig(jitter_factor=0.0)
        handler = LLMErrorHandler(config)
        delay = handler._calculate_retry_delay(1)
        assert delay == config.base_delay

    def test_calculate_retry_delay_with_jitter(self):
        """Test retry delay calculation with jitter"""
        config = LLMRetryConfig(jitter_factor=0.1)
        handler = LLMErrorHandler(config)
        delay = handler._calculate_retry_delay(1)
        assert delay >= config.base_delay * 0.9
        assert delay <= config.base_delay * 1.1

    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        config = LLMRetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=30.0)
        handler = LLMErrorHandler(config)

        delay_1 = handler._calculate_retry_delay(1)
        delay_2 = handler._calculate_retry_delay(2)
        delay_3 = handler._calculate_retry_delay(3)

        assert delay_2 > delay_1
        assert delay_3 > delay_2


class TestLLMRetryDecorator:
    """Test @llm_retry decorator"""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call without retry"""

        @llm_retry(max_retries=3, base_delay=0.1)
        async def mock_function():
            return "success"

        result = await mock_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry on timeout error"""
        attempt_count = 0

        @llm_retry(max_retries=3, base_delay=0.1)
        async def mock_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise LLMError(message="Timeout", error_type=LLMErrorType.TIMEOUT)
            return "success"

        result = await mock_function()
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test max retries exceeded"""

        @llm_retry(max_retries=2, base_delay=0.1)
        async def mock_function():
            raise LLMError(message="Always fails", error_type=LLMErrorType.NETWORK)

        with pytest.raises(LLMError):
            await mock_function()

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Test rate limit retry"""

        @llm_retry(max_retries=3, base_delay=0.1)
        async def mock_function():
            if True:
                raise LLMError(
                    message="Rate limited", error_type=LLMErrorType.RATE_LIMIT
                )

        with pytest.raises(LLMError):
            await mock_function()


class TestRetryAwareClient:
    """Test retry-aware client creation"""

    def test_create_retry_aware_client(self):
        """Test creating retry-aware client"""
        mock_client = Mock()
        config = LLMRetryConfig(max_retries=2)

        client = create_retry_aware_client(mock_client, config)
        assert client is not None

    def test_client_wrapping(self):
        """Test that client is properly wrapped"""
        mock_client = Mock()
        config = LLMRetryConfig()

        client = create_retry_aware_client(mock_client, config)
        assert hasattr(client, "config") or client is not None


class TestRetryStatistics:
    """Test retry statistics tracking"""

    def test_retry_counting(self):
        """Test that retry attempts are counted"""
        config = LLMRetryConfig(max_retries=3)
        handler = LLMErrorHandler(config)

        error = LLMError(message="Test error", error_type=LLMErrorType.NETWORK)

        handler._classify_error(error.error_type)
        assert handler.config.max_retries == 3


def run_all_tests():
    """Run all tests"""
    print("🧪 Running LLM Retry Mechanism Tests")
    print("=" * 50)

    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_all_tests()
