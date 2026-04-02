"""Transform a semantic (natural language) query into a boolean search query using an LLM."""

import logging
import re

from llm_client import call_llm

logger = logging.getLogger(__name__)

# Prompts séparés : PubMed (avec MeSH) vs sources neutres (sans MeSH)
SYSTEM_PROMPT_PUBMED = {
    "fr": (
        "Tu es un expert en recherche bibliographique scientifique. "
        "Transforme la requête en langage naturel en requête booléenne optimisée pour PubMed.\n\n"
        "Règles :\n"
        "- Utilise les opérateurs AND, OR, NOT en majuscules\n"
        "- Ajoute des synonymes et variantes pertinentes avec OR\n"
        "- Utilise des guillemets pour les expressions exactes\n"
        "- Ajoute des termes MeSH pertinents entre crochets [MeSH] quand applicable\n"
        "- Garde la requête concise mais exhaustive\n"
        "- Réponds UNIQUEMENT avec la requête booléenne, sans explication ni commentaire"
    ),
    "en": (
        "You are an expert in scientific literature searching. "
        "Transform the natural language query into an optimized boolean query for PubMed.\n\n"
        "Rules:\n"
        "- Use AND, OR, NOT operators in uppercase\n"
        "- Add relevant synonyms and variants with OR\n"
        "- Use quotes for exact phrases\n"
        "- Add relevant MeSH terms in brackets [MeSH] when applicable\n"
        "- Keep the query concise but comprehensive\n"
        "- Reply ONLY with the boolean query, no explanation or commentary"
    ),
}

SYSTEM_PROMPT_NEUTRAL = {
    "fr": (
        "Tu es un expert en recherche bibliographique scientifique. "
        "Transforme la requête en langage naturel en requête booléenne simple, "
        "compatible avec Semantic Scholar et Europe PMC.\n\n"
        "Règles :\n"
        "- Utilise les opérateurs AND, OR, NOT en majuscules\n"
        "- Ajoute des synonymes et variantes pertinentes avec OR\n"
        "- Utilise des guillemets pour les expressions exactes\n"
        "- N'utilise PAS de tags spécifiques à PubMed comme [MeSH], [tiab], [tw]\n"
        "- Garde la requête concise mais exhaustive\n"
        "- Réponds UNIQUEMENT avec la requête booléenne, sans explication ni commentaire"
    ),
    "en": (
        "You are an expert in scientific literature searching. "
        "Transform the natural language query into a simple boolean query "
        "compatible with Semantic Scholar and Europe PMC.\n\n"
        "Rules:\n"
        "- Use AND, OR, NOT operators in uppercase\n"
        "- Add relevant synonyms and variants with OR\n"
        "- Use quotes for exact phrases\n"
        "- Do NOT use PubMed-specific tags like [MeSH], [tiab], [tw]\n"
        "- Keep the query concise but comprehensive\n"
        "- Reply ONLY with the boolean query, no explanation or commentary"
    ),
}

USER_PROMPT = {
    "fr": "Transforme cette requête en langage naturel en requête booléenne optimisée :\n\n{query}",
    "en": "Transform this natural language query into an optimized boolean query:\n\n{query}",
}


def _clean_llm_output(text: str) -> str:
    """Supprime les balises markdown de code que le LLM pourrait ajouter."""
    text = text.strip()
    # Supprime les blocs ```...``` (avec ou sans langage spécifié)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def transform_query(
    semantic_query: str,
    llm_provider: str,
    lang: str = "fr",
    target: str = "pubmed",
) -> str:
    """Convertit une requête en langage naturel en requête booléenne.

    Args:
        semantic_query: Requête en langage naturel de l'utilisateur
        llm_provider: Fournisseur LLM à utiliser
        lang: Langue des prompts ('fr' ou 'en')
        target: Source cible — 'pubmed' (avec MeSH) ou 'neutral' (sans tags PubMed)

    Returns:
        Requête booléenne sous forme de chaîne
    """
    if target == "pubmed":
        system = SYSTEM_PROMPT_PUBMED.get(lang, SYSTEM_PROMPT_PUBMED["en"])
    else:
        system = SYSTEM_PROMPT_NEUTRAL.get(lang, SYSTEM_PROMPT_NEUTRAL["en"])

    user = USER_PROMPT.get(lang, USER_PROMPT["en"]).format(query=semantic_query)

    logger.info(f"Transformation sémantique [{target}] avec {llm_provider}: {semantic_query}")

    boolean_query = call_llm(
        provider=llm_provider,
        system_prompt=system,
        user_prompt=user,
        max_tokens=512,
    )

    boolean_query = _clean_llm_output(boolean_query)

    logger.info(f"Requête booléenne [{target}]: {boolean_query}")
    return boolean_query
