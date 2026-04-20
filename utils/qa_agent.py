"""Agent Q&A — Répond aux questions de suivi sans relancer la pipeline."""

import logging

from llm_client import call_llm
from models import Article

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "fr": (
        "Tu es un expert scientifique qui vient de produire une revue bibliographique. "
        "Tu réponds aux questions de suivi de l'utilisateur en t'appuyant UNIQUEMENT sur :\n"
        "1. Le rapport de synthèse fourni ci-dessous\n"
        "2. Les métadonnées des articles du corpus\n"
        "3. L'historique de la conversation\n\n"
        "RÈGLES IMPÉRATIVES :\n"
        "- Ne cite que des informations présentes dans le rapport ou le corpus\n"
        "- Indique les sources (titre, auteurs, année) quand tu cites un fait précis\n"
        "- Si l'information n'est pas dans le corpus, dis-le clairement\n"
        "- Réponds en français\n"
        "- Sois concis et précis"
    ),
    "en": (
        "You are a scientific expert who just produced a bibliographic review. "
        "You answer follow-up questions from the user based ONLY on:\n"
        "1. The synthesis report provided below\n"
        "2. Article corpus metadata\n"
        "3. The conversation history\n\n"
        "MANDATORY RULES:\n"
        "- Only cite information present in the report or corpus\n"
        "- Indicate sources (title, authors, year) when citing a specific fact\n"
        "- If the information is not in the corpus, say so clearly\n"
        "- Reply in English\n"
        "- Be concise and precise"
    ),
}


def _build_context(report_markdown: str, articles: list[Article], lang: str) -> str:
    """Construit le contexte à fournir au LLM (rapport + corpus résumé)."""
    # Résumé léger du corpus (titres + auteurs + année + DOI)
    corpus_lines = []
    for a in articles[:80]:  # cap pour éviter de dépasser les tokens
        authors_str = ", ".join(a.authors[:3]) + ("…" if len(a.authors) > 3 else "")
        doi_str = f" DOI:{a.doi}" if a.doi else ""
        corpus_lines.append(f"- {a.title} — {authors_str} ({a.year}){doi_str}")
    corpus_summary = "\n".join(corpus_lines)

    if lang == "fr":
        return (
            f"=== RAPPORT DE SYNTHÈSE ===\n\n{report_markdown}\n\n"
            f"=== LISTE DES ARTICLES DU CORPUS ===\n\n{corpus_summary}"
        )
    else:
        return (
            f"=== SYNTHESIS REPORT ===\n\n{report_markdown}\n\n"
            f"=== ARTICLE CORPUS LIST ===\n\n{corpus_summary}"
        )


def answer_question(
    question: str,
    report_markdown: str,
    articles: list[Article],
    chat_history: list[dict],
    lang: str,
    llm_provider: str,
) -> str:
    """Répond à une question de suivi en s'appuyant sur le corpus et le rapport.

    Args:
        question: Question de l'utilisateur
        report_markdown: Rapport de synthèse généré par Agent 2
        articles: Liste des articles du corpus
        chat_history: Historique [{role: 'user'|'assistant', content: str}]
        lang: Langue de la réponse ('fr' ou 'en')
        llm_provider: Fournisseur LLM à utiliser

    Returns:
        Réponse de l'agent sous forme de texte markdown
    """
    system = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])
    context = _build_context(report_markdown, articles, lang)

    # Construction du prompt utilisateur avec historique
    history_parts = []
    for msg in chat_history[-6:]:  # 6 derniers échanges = 3 tours
        role_label = ("Utilisateur" if lang == "fr" else "User") if msg["role"] == "user" \
            else ("Assistant" if lang == "fr" else "Assistant")
        history_parts.append(f"{role_label}: {msg['content']}")

    history_block = "\n\n".join(history_parts)
    history_section = ""
    if history_block:
        header = "=== HISTORIQUE DE LA CONVERSATION ===" if lang == "fr" \
            else "=== CONVERSATION HISTORY ==="
        history_section = f"\n\n{header}\n\n{history_block}"

    new_question_label = "=== NOUVELLE QUESTION ===" if lang == "fr" else "=== NEW QUESTION ==="
    user_prompt = f"{context}{history_section}\n\n{new_question_label}\n\n{question}"

    logger.info(f"Q&A [{llm_provider}]: {question[:80]}")

    try:
        answer = call_llm(
            provider=llm_provider,
            system_prompt=system,
            user_prompt=user_prompt,
            max_tokens=2048,
        )
        return answer.strip()
    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        error_msg = f"Erreur lors de la réponse : {e}" if lang == "fr" \
            else f"Error generating response: {e}"
        return error_msg
