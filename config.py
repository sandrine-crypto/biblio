"""Configuration globale de l'application."""

import os


def _get_secret(key: str, default: str = "") -> str:
    """Lit un secret depuis st.secrets (Streamlit Cloud) ou os.environ (local)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = _get_secret("PERPLEXITY_API_KEY")
MISTRAL_API_KEY = _get_secret("MISTRAL_API_KEY")
NCBI_API_KEY = _get_secret("NCBI_API_KEY")
NCBI_EMAIL = _get_secret("NCBI_EMAIL", "biblio@example.com")

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
PERPLEXITY_MODEL = "llama-3.1-sonar-large-128k-online"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MISTRAL_MODEL = "mistral-large-latest"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

MAX_RESULTS_PER_SOURCE = 50
DEDUP_TITLE_THRESHOLD = 90
TOKEN_ESTIMATE_DIVISOR = 4
MAX_TOKENS_SINGLE_CALL = 150_000
CHUNK_TOKEN_SIZE = 80_000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
