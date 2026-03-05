"""Client Europe PMC REST API."""

import logging
import time
import requests

import config
from models import Article

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search_europe_pmc(keywords: str, date_from: str, date_to: str, max_results: int | None = None) -> list[Article]:
    """Recherche Europe PMC et retourne une liste d'Articles."""
    articles = []
    if max_results is None:
        max_results = config.MAX_RESULTS_PER_SOURCE

    try:
        year_from = date_from.split("/")[0] if "/" in date_from else date_from[:4]
        year_to = date_to.split("/")[0] if "/" in date_to else date_to[:4]

        query = f"{keywords} (FIRST_PDATE:[{year_from}-01-01 TO {year_to}-12-31])"
        logger.info(f"Europe PMC search: {query}")

        cursor_mark = "*"
        page_size = min(max_results, 25)

        while len(articles) < max_results:
            params = {
                "query": query,
                "format": "json",
                "pageSize": page_size,
                "cursorMark": cursor_mark,
                "resultType": "core",
            }

            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("resultList", {}).get("result", [])
            if not results:
                break

            for result in results:
                try:
                    article = _parse_result(result)
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Europe PMC: erreur parsing: {e}")

            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor

            time.sleep(0.5)

        logger.info(f"Europe PMC: {len(articles)} articles collectés")

    except Exception as e:
        logger.error(f"Europe PMC search error: {e}")

    return articles[:max_results]


def _parse_result(result: dict) -> Article:
    """Parse un résultat Europe PMC en Article."""
    title = result.get("title", "") or ""

    authors_str = result.get("authorString", "") or ""
    authors = [a.strip() for a in authors_str.split(",") if a.strip()] if authors_str else []

    doi = result.get("doi")

    journal = result.get("journalTitle")

    year = None
    pub_year = result.get("pubYear")
    if pub_year:
        try:
            year = int(pub_year)
        except ValueError:
            pass

    abstract = result.get("abstractText")

    keywords = []
    kw_list = result.get("keywordList", {}).get("keyword", [])
    if kw_list:
        keywords = [str(kw) for kw in kw_list]

    citation_count = result.get("citedByCount", 0) or 0

    return Article(
        title=title,
        authors=authors,
        doi=doi,
        journal=journal,
        year=year,
        abstract=abstract,
        keywords=keywords,
        citation_count=citation_count,
        source="europe_pmc",
    )
