"""
groq_client.py

Client for interacting with Groq API for AI-powered code analysis and fix generation.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Default Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_groq_api_key() -> str:
    """Retrieve the Groq API key from environment variables."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    return api_key


def call_groq(system_prompt: str, user_prompt: str, model: str = "llama-3.1-70b-versatile") -> str:
    """
    Call the Groq API with a system prompt and user prompt.

    Args:
        system_prompt: The system instructions that define the AI's role and behavior.
        user_prompt: The user's input/query.
        model: The Groq model to use (default: llama-3.1-70b-versatile).

    Returns:
        The model's response as a string.

    Raises:
        ValueError: If the API key is not configured.
        Exception: If the API call fails.
    """
    try:
        import requests

        api_key = get_groq_api_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }

        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        logger.info("Groq API call successful")
        return content

    except ImportError:
        logger.warning("requests library not available, returning mock response")
        return f"Mock response to: {user_prompt[:100]}..."
    except Exception as exc:
        logger.error("Groq API call failed: %s", exc)
        raise
