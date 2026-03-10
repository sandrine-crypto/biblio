"""Transform a semantic (natural language) query into a boolean search query using an LLM."""

import logging

from llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = {
    "fr": (
        "Tu es un expert en recherche bibliographique scientifique. "
        "Ton role est de transformer une requete en langage naturel en une requete booleenne "
        "optimisee pour les bases de donnees scientifiques (PubMed, Semantic Scholar, Europe PMC).\n\n"
        "Regles :\n"
        "- Utilise les operateurs AND, OR, NOT\n"
        "- Ajoute des synonymes et variantes pertinentes avec OR\n"
        "- Utilise des guillemets pour les expressions exactes\n"
        "- Ajoute des termes MeSH pertinents entre crochets [MeSH] quand c'est applicable\n"
        "- Garde la requete concise mais exhaustive\n"
        "- Reponds UNIQUEMENT avec la requete booleenne, sans explication ni commentaire"
    ),
    "en": (
        "You are an expert in scientific literature searching. "
        "Your role is to transform a natural language query into an optimized boolean search query "
        "for scientific databases (PubMed, Semantic Scholar, Europe PMC).\n\n"
        "Rules:\n"
        "- Use AND, OR, NOT operators\n"
        "- Add relevant synonyms and variants with OR\n"
        "- Use quotes for exact phrases\n"
        "- Add relevant MeSH terms in brackets [MeSH] when applicable\n"
        "- Keep the query concise but comprehensive\n"
        "- Reply ONLY with the boolean query, no explanation or commentary"
    ),
}

USER_PROMPT = {
    "fr": "Transforme cette requete en langage naturel en requete booleenne optimisee :\n\n{query}",
    "en": "Transform this natural language query into an optimized boolean query:\n\n{query}",
}


def transform_query(
    semantic_query: str,
    llm_provider: str,
    lang: str = "fr",
) -> str:
    """Convert a natural language query to a boolean search query using an LLM.

    Args:
        semantic_query: The user's natural language query
        llm_provider: LLM provider to use for transformation
        lang: Language for prompts

    Returns:
        Boolean search query string
    """
    system = SYSTEM_PROMPT.get(lang, SYSTEM_PROMPT["en"])
    user = USER_PROMPT.get(lang, USER_PROMPT["en"]).format(query=semantic_query)

    logger.info(f"Transforming semantic query with {llm_provider}: {semantic_query}")

    boolean_query = call_llm(
        provider=llm_provider,
        system_prompt=system,
        user_prompt=user,
        max_tokens=512,
    )

    # Clean up: remove any markdown formatting the LLM might add
    boolean_query = boolean_query.strip()
    for prefix in ["```", "```text", "```boolean"]:
        if boolean_query.startswith(prefix):
            boolean_query = boolean_query[len(prefix):]
    if boolean_query.endswith("```"):
        boolean_query = boolean_query[:-3]
    boolean_query = boolean_query.strip()

    logger.info(f"Boolean query result: {boolean_query}")
    return boolean_query
