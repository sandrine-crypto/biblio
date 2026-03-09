"""Unified LLM client — supports Claude, Mistral, and Perplexity."""

import json
import logging
import re

import requests as req

import config

logger = logging.getLogger(__name__)

# Provider constants
CLAUDE = "claude"
MISTRAL = "mistral"
PERPLEXITY = "perplexity"

PROVIDER_LABELS = {
    CLAUDE: "Claude (Anthropic)",
    MISTRAL: "Mistral AI",
    PERPLEXITY: "Perplexity",
}


def get_api_key(provider: str) -> str:
    """Return the API key for the given provider."""
    if provider == CLAUDE:
        return config.ANTHROPIC_API_KEY
    elif provider == MISTRAL:
        return config.MISTRAL_API_KEY
    elif provider == PERPLEXITY:
        return config.PERPLEXITY_API_KEY
    return ""


def is_provider_available(provider: str) -> bool:
    """Check if the provider's API key is configured."""
    return bool(get_api_key(provider))


def call_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 8192,
) -> str:
    """Send a prompt to the specified LLM provider and return the text response.

    Args:
        provider: One of 'claude', 'mistral', 'perplexity'
        system_prompt: System instructions
        user_prompt: User message
        max_tokens: Maximum tokens in response

    Returns:
        Response text from the LLM
    """
    api_key = get_api_key(provider)
    if not api_key:
        raise ValueError(f"API key not configured for {PROVIDER_LABELS.get(provider, provider)}")

    if provider == CLAUDE:
        return _call_claude(api_key, system_prompt, user_prompt, max_tokens)
    elif provider == MISTRAL:
        return _call_mistral(api_key, system_prompt, user_prompt, max_tokens)
    elif provider == PERPLEXITY:
        return _call_perplexity(api_key, system_prompt, user_prompt, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_llm_json(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
) -> dict:
    """Call LLM and parse JSON from response."""
    text = call_llm(provider, system_prompt, user_prompt, max_tokens)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(text)


# ─── Provider implementations ────────────────────────────────────────────────


def _call_claude(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _call_mistral(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    response = req.post(config.MISTRAL_API_URL, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_perplexity(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.PERPLEXITY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    response = req.post(config.PERPLEXITY_API_URL, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
