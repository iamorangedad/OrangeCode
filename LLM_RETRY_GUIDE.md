# LLM API Error Handling and Retry Mechanism

## Overview

This document describes the robust LLM API error handling and retry mechanism implemented for Orange Code, providing production-ready resilience against network issues, service unavailability, and rate limiting.

## Features

### 🔄 Intelligent Retry Mechanism
- **Exponential Backoff**: Delays increase exponentially between retries
- **Random Jitter**: Prevents thundering herd problems during retries
- **Configurable Limits**: Set maximum retries, delays, and jitter factor
- **Error Classification**: Different retry strategies for different error types
- **Statistics Tracking**: Comprehensive metrics on retry attempts and success rates

### 🛡️ Error Classification System
- **Rate Limiting**: Automatic detection and appropriate retry timing
- **Timeout Handling**: Intelligent timeout management
- **Service Unavailable**: Graceful handling when LLM service is down
- **Authentication Errors**: Proper handling of auth failures
- **Network Issues**: Retry with appropriate delays
- **Model Errors**: Handle model not found or unavailable scenarios
- **Server Errors**: Retry for 5xx server errors
- **Invalid Requests**: Retry malformed requests

### 🔧 Key Components

#### LLMRetryConfig
```python
config = LLMRetryConfig(
    max_retries=3,           # Maximum retry attempts
    base_delay=1.0,          # Base delay in seconds
    max_delay=30.0,          # Maximum delay in seconds
    exponential_base=2.0,      # Base for exponential backoff
    jitter_factor=0.1           # Random jitter factor (0-1)
    retryable_errors=[...]        # Configurable error types to retry
)
```

#### @llm_retry Decorator
```python
@llm_retry(max_retries=3)
async def enhanced_api_call():
    # Automatic retry with exponential backoff and jitter
    # Intelligently retries only appropriate errors
```

#### LLMErrorHandler
```python
handler = LLMErrorHandler(config)

# Rich logging with retry statistics
handler.log_retry_attempt(...)
handler.log_success(...)
handler.log_final_failure(...)
```

#### LLMClientWithRetry
```python
client = LLMClientWithRetry(base_client, config)

# Enhanced client with built-in retry mechanism
await client.chat_with_retry(...)
```

#### ToolExecutor
```python
executor = ToolExecutor(retry_client)

# Smart tool execution with LLM planning and validation
await executor.execute_tool_with_llm_planning(...)
await executor.execute_tool_with_llm_validation(...)
```

## 📊 Usage Examples

### Basic Usage
```python
# Simple retry with default configuration
@llm_retry(max_retries=3)
async def api_call():
    response = await client.chat_with_retry(
        model="qwen2.5-coder:3b",
        messages=messages
    )
```

### Custom Configuration
```python
# Configuration for高峰期 (shorter delays, more jitter)
config = LLMRetryConfig(
    max_retries=3,
    base_delay=0.5,      # Shorter base delay for responsiveness
    max_delay=15.0,      # Shorter max delay
    exponential_base=1.8,    # Less aggressive backoff
    jitter_factor=0.2       # More jitter for load distribution
)

@llm_retry(config=config)
async def api_call():
    response = await client.chat_with_retry(...)
```

### Error-Specific Configuration
```python
# Only retry on network errors, not on validation errors
retryable_errors=[
    LLMErrorType.RATE_LIMIT,
    LLMErrorType.TIMEOUT,
    LLMErrorType.NETWORK_ERROR,
    LLMErrorType.SERVICE_UNAVAILABLE
]
```

### Success Rate Monitoring
```python
# Get detailed statistics
stats = client.get_retry_stats()

# Monitor success rate
success_rate = stats['successful_calls'] / stats['total_calls']
if success_rate < 0.95:
    # Implement circuit breaker or rate limiting
```

## 🎯 Benefits

### 1. Resilience
- **Automatic Recovery**: Handles transient failures without manual intervention
- **Load Distribution**: Spreads retries across time to avoid overwhelming the service
- **Graceful Degradation**: Implements circuit breaker pattern for extended outages

### 2. User Experience
- **Transparent Retry**: Users see retry attempts and progress
- **Rich Logging**: Detailed logs for debugging and monitoring
- **No Silent Failures**: Clear error messages with retry context

### 3. Operational Efficiency
- **Higher Success Rate**: Exponential backoff and jitter improve success probability
- **Reduced Manual Intervention**: Most failures are handled automatically
- **Predictable Performance**: Consistent retry behavior enables capacity planning

### 4. Configuration Flexibility
- **Environment-Specific**: Different configurations for development vs production
- **Per-Service Tuning**: Optimize retry parameters for different LLM services
- **Dynamic Adjustment**: Runtime configuration changes without code deployment

## 🔧 Integration

The retry mechanism is fully integrated with:

1. **Tool Registration System**: Automatically applies to all registered tools
2. **Permission Management**: Respects skill-based access control
3. **AgentScheduler**: Enhanced with intelligent retry logic
4. **CLI Interface**: New commands for retry statistics and configuration

## 🚀 Production Ready

This implementation follows industry best practices for:
- Fault tolerance and resilience
- Monitoring and observability
- Configuration flexibility
- User experience optimization
- Error handling and reporting