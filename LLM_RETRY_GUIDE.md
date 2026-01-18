# LLM Retry Mechanism

Orange Code includes intelligent retry logic for resilient LLM API calls.

## Features

- **Exponential Backoff**: Retry delays increase exponentially
- **Random Jitter**: Prevents thundering herd problems
- **Error Classification**: Different strategies for different error types
- **Configurable Limits**: Control retry attempts and timing

## Configuration

```python
from retry import LLMRetryConfig

config = LLMRetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter_factor=0.1
)
```

## Usage

```python
from retry import create_retry_aware_client

# Create client with retry
client = create_retry_aware_client(
    ollama_client,
    config=config
)

# Use retry decorator
@llm_retry(max_retries=3, base_delay=1.0)
async def generate_code(prompt):
    return await client.generate(prompt)
```

## Error Handling

The system automatically handles:
- Rate limiting (429)
- Timeouts
- Service unavailability (503)
- Network issues
- Server errors (5xx)

## Implementation

See `retry.py` for complete implementation details.