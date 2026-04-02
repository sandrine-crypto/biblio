"""Client Semantic Scholar API."""

import logging
import time
import requests

import config
from models import Article

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,authors,year,abstract,journal,externalIds,citationCount,fieldsOfStudy"


def search_semantic_scholar(
    keywords: str, date_from: str, date_to: str, max_results: int | None = None
) -> list[Article]:
    """Recherche Semantic Scholar et retourne une liste d'Articles."""
    articles = []
    if max_results is None:
        max_results = config.MAX_RESULTS_PER_SOURCE

    year_from = date_from.split("/")[0] if "/" in date_from else date_from[:4]
    year_to = date_to.split("/")[0] if "/" in date_to else date_to[:4]

    params = {
        "query": keywords,
        "fields": FIELDS,
        "limit": min(max_results, 100),
        "year": f"{year_from}-{year_to}",
    }

    # Utilise la clé API si disponible (augmente le rate-limit)
    headers = {}
    api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key

    logger.info(f"Semantic Scholar search: {keywords} ({year_from}-{year_to})")

    offset = 0
    while len(articles) < max_results:
        params["offset"] = offset
        try:
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
        except requests.RequestException as e:
            logger.error(f"Semantic Scholar: erreur réseau: {e}")
            break

        if response.status_code == 429:
            logger.warning("Semantic Scholar: rate limited, attente 5s...")
            time.sleep(5)
            continue

        response.raise_for_status()
        data = response.json()

        papers = data.get("data", [])
        if not papers:
            break

        for paper in papers:
            try:
                article = _parse_paper(paper)
                articles.append(article)
            except Exception as e:
                logger.warning(f"Semantic Scholar: erreur parsing: {e}")

        total = data.get("total", 0)
        offset += len(papers)
        if offset >= total or offset >= max_results:
            break

        time.sleep(1)  # Respect du rate-limit

    logger.info(f"Semantic Scholar: {len(articles)} articles collectés")
    return articles[:max_results]


def _parse_paper(paper: dict) -> Article:
    """Parse un résultat Semantic Scholar en Article."""
    title = paper.get("title", "") or ""

    authors = [
        author.get("name", "")
        for author in paper.get("authors", [])
        if author.get("name")
    ]

    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI")

    journal_info = paper.get("journal") or {}
    journal = journal_info.get("name") if isinstance(journal_info, dict) else None

    year = paper.get("year")
    abstract = paper.get("abstract")
    keywords = paper.get("fieldsOfStudy") or []
    citation_count = paper.get("citationCount") or 0

    return Article(
        title=title,
        authors=authors,
        doi=doi,
        journal=journal,
        year=year,
        abstract=abstract,
        keywords=keywords,
        citation_count=citation_count,
        source="semantic_scholar",
    )
