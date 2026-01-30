#!/usr/bin/env python3
"""
Configuration Module for AI Swarm System

Handles API authentication, model configuration, and cost tracking.
"""

import os
import sys


# API Configuration
ANTHROPIC_API_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# Default Model Settings
DEFAULT_MODEL = "claude-3-haiku-20240307"
DEFAULT_MAX_TOKENS = 1024

# Retry Configuration
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30  # seconds

# Lock Contention Mitigation
JITTER_RANGE = (0, 1)  # Random jitter in seconds for status updates


def get_api_endpoint():
    """
    Get API endpoint from environment variable or use default

    Supports ccswitch proxy via LLM_BASE_URL environment variable.

    Returns:
        str: API endpoint URL
    """
    return os.environ.get('LLM_BASE_URL', ANTHROPIC_API_ENDPOINT)


def is_proxy_mode():
    """
    Check if running in proxy mode (ccswitch)

    Returns:
        bool: True if LLM_BASE_URL is set (proxy mode)
    """
    return bool(os.environ.get('LLM_BASE_URL'))


def get_api_key():
    """
    Get Anthropic API key from environment variable

    In proxy mode (ccswitch), API key is optional.
    In direct mode, API key is required.

    Returns:
        str: API key or empty string if proxy mode

    Raises:
        RuntimeError: If API key required but not set
    """
    # Proxy mode doesn't require API key
    if is_proxy_mode():
        return os.environ.get('ANTHROPIC_API_KEY', '')

    # Direct mode requires API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        raise RuntimeError(
            "Error: ANTHROPIC_API_KEY environment variable not set\n"
            "Get your API key at: https://console.anthropic.com/\n"
            "Run: export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "Or use ccswitch proxy: export LLM_BASE_URL='https://...'"
        )

    return api_key

# Model Pricing (per 1M tokens)
MODEL_PRICING = {
    'claude-3-haiku-20240307': {
        'input': 0.25,
        'output': 1.25
    },
    'claude-3-sonnet-20240229': {
        'input': 3.0,
        'output': 15.0
    },
    'claude-3-opus-20240229': {
        'input': 15.0,
        'output': 75.0
    }
}

# Valid Claude 3 Models
VALID_MODELS = set(MODEL_PRICING.keys())

# Maximum tokens per model
MODEL_MAX_LIMITS = {
    'claude-3-haiku-20240307': 4096,
    'claude-3-sonnet-20240229': 4096,
    'claude-3-opus-20240229': 4096,
}


def validate_api_key_format(api_key=None):
    """
    Validate API key format

    Accepts any non-empty string to support proxy services (e.g., ccswitch).

    Args:
        api_key: API key to validate (default: load from environment)

    Returns:
        bool: True if format is valid, False otherwise
    """
    if api_key is None:
        try:
            api_key = get_api_key()
        except RuntimeError:
            return False

    # Accept any non-empty string (supports proxy services like ccswitch)
    return bool(api_key and len(api_key) > 0)


def calculate_cost(model, input_tokens, output_tokens):
    """
    Calculate API cost for a request

    Args:
        model: Model name (e.g., 'claude-3-haiku-20240307')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        float: Cost in USD
    """
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model: {model}")

    pricing = MODEL_PRICING[model]

    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']

    return input_cost + output_cost


def validate_model(model):
    """
    Validate model name

    Args:
        model: Model name to validate

    Returns:
        bool: True if model is valid, False otherwise
    """
    return model in VALID_MODELS


def validate_max_tokens(max_tokens, model=None):
    """
    Validate max_tokens value

    Args:
        max_tokens: Maximum tokens value
        model: Model name (optional, for model-specific limits)

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        return False

    if model and model in MODEL_MAX_LIMITS:
        return max_tokens <= MODEL_MAX_LIMITS[model]

    # Default limit
    return max_tokens <= DEFAULT_MAX_TOKENS or max_tokens <= 4096


def get_model_max_tokens(model):
    """
    Get maximum tokens for a model

    Args:
        model: Model name

    Returns:
        int: Maximum tokens allowed
    """
    return MODEL_MAX_LIMITS.get(model, DEFAULT_MAX_TOKENS)


def estimate_cost(model, max_tokens):
    """
    Estimate maximum cost for a request

    Args:
        model: Model name
        max_tokens: Maximum tokens to generate

    Returns:
        float: Estimated cost in USD
    """
    # Assume 1:1 input:output ratio for estimation
    estimated_input = max_tokens / 2
    estimated_output = max_tokens / 2

    return calculate_cost(model, estimated_input, estimated_output)
