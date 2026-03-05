"""Configuration globale de l'application."""

import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "biblio@example.com")

ANTHROPIC_MODEL = "claude-opus-4-6"
PERPLEXITY_MODEL = "llama-3.1-sonar-large-128k-online"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

MAX_RESULTS_PER_SOURCE = 50
DEDUP_TITLE_THRESHOLD = 90
TOKEN_ESTIMATE_DIVISOR = 4
MAX_TOKENS_SINGLE_CALL = 150_000
CHUNK_TOKEN_SIZE = 80_000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
