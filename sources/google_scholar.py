"""Client Google Scholar via scholarly (avec fallback gracieux)."""

import logging
import time

from config import MAX_RESULTS_PER_SOURCE
from models import Article

logger = logging.getLogger(__name__)


def search_google_scholar(keywords: str, date_from: str, date_to: str, max_results: int = MAX_RESULTS_PER_SOURCE) -> list[Article]:
    """Recherche Google Scholar via scholarly. Retourne liste vide si bloqué."""
    articles = []

    try:
        from scholarly import scholarly

        year_from = int(date_from.split("/")[0]) if "/" in date_from else int(date_from[:4])
        year_to = int(date_to.split("/")[0]) if "/" in date_to else int(date_to[:4])

        logger.info(f"Google Scholar search: {keywords} ({year_from}-{year_to})")

        search_query = scholarly.search_pubs(keywords, year_low=year_from, year_high=year_to)

        count = 0
        for result in search_query:
            if count >= min(max_results, 20):  # Limit to avoid blocking
                break

            try:
                article = _parse_result(result)
                articles.append(article)
                count += 1
            except Exception as e:
                logger.warning(f"Google Scholar: erreur parsing: {e}")

            time.sleep(5)  # Conservative rate limiting

        logger.info(f"Google Scholar: {len(articles)} articles collectés")

    except ImportError:
        logger.warning("Google Scholar: module 'scholarly' non installé")
    except Exception as e:
        logger.warning(f"Google Scholar indisponible (probablement bloqué): {e}")
        logger.info("Les résultats des autres sources seront utilisés")

    return articles


def _parse_result(result: dict) -> Article:
    """Parse un résultat scholarly en Article."""
    bib = result.get("bib", {})

    title = bib.get("title", "") or ""

    authors = bib.get("author", []) or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(" and ")]

    year = None
    year_str = bib.get("pub_year", "")
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            pass

    abstract = bib.get("abstract", "")

    journal = bib.get("venue", "") or bib.get("journal", "")

    # scholarly doesn't always provide DOI
    doi = None
    eprint = result.get("eprint_url", "")
    pub_url = result.get("pub_url", "")
    for url in [eprint, pub_url]:
        if url and "doi.org/" in url:
            doi = url.split("doi.org/")[-1]
            break

    citation_count = result.get("num_citations", 0) or 0

    return Article(
        title=title,
        authors=authors,
        doi=doi,
        journal=journal if journal else None,
        year=year,
        abstract=abstract if abstract else None,
        keywords=[],
        citation_count=citation_count,
        source="google_scholar",
    )
