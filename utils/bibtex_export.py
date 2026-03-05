"""Export des articles au format BibTeX."""

import logging
import os
import re

from config import OUTPUT_DIR
from models import Article

logger = logging.getLogger(__name__)


def _sanitize_key(text: str) -> str:
    """Génère une clé BibTeX valide à partir du titre/auteur."""
    text = re.sub(r'[^\w]', '', text)
    return text[:30] if text else "unknown"


def _escape_bibtex(text: str) -> str:
    """Échappe les caractères spéciaux BibTeX."""
    if not text:
        return ""
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("#", r"\#")
    text = text.replace("_", r"\_")
    return text


def generate_bibtex(articles: list[Article], output_path: str | None = None) -> str:
    """Génère un fichier BibTeX à partir de la liste d'articles.

    Args:
        articles: Liste d'articles
        output_path: Chemin de sortie (optionnel)

    Returns:
        Contenu BibTeX en string
    """
    entries = []

    for i, article in enumerate(articles):
        # Generate key
        first_author = article.authors[0].split()[-1] if article.authors else "Unknown"
        year = str(article.year) if article.year else "nd"
        key = _sanitize_key(first_author) + year + f"_{i}"

        lines = [f"@article{{{key},"]
        lines.append(f"  title = {{{_escape_bibtex(article.title)}}},")

        if article.authors:
            authors_str = " and ".join(article.authors)
            lines.append(f"  author = {{{_escape_bibtex(authors_str)}}},")

        if article.journal:
            lines.append(f"  journal = {{{_escape_bibtex(article.journal)}}},")

        if article.year:
            lines.append(f"  year = {{{article.year}}},")

        if article.doi:
            lines.append(f"  doi = {{{article.doi}}},")

        if article.abstract:
            abstract_short = article.abstract[:500]
            lines.append(f"  abstract = {{{_escape_bibtex(abstract_short)}}},")

        if article.keywords:
            kw_str = ", ".join(article.keywords)
            lines.append(f"  keywords = {{{_escape_bibtex(kw_str)}}},")

        lines.append("}")
        entries.append("\n".join(lines))

    bibtex_content = "\n\n".join(entries)

    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, "references.bib")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bibtex_content)

    logger.info(f"BibTeX généré: {len(entries)} entrées → {output_path}")
    return bibtex_content
