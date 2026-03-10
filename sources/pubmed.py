"""Client PubMed via NCBI E-utilities HTTP API (no Biopython dependency)."""

import logging
import time
import xml.etree.ElementTree as ET

import requests

import config
from models import Article

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pubmed(keywords: str, date_from: str, date_to: str, max_results: int | None = None) -> list[Article]:
    """Search PubMed and return a list of Articles.

    Uses the NCBI E-utilities HTTP API directly (no Biopython).
    Raises on network/API errors so the caller can display them.
    """
    if max_results is None:
        max_results = config.MAX_RESULTS_PER_SOURCE

    # ---- Step 1: esearch to get PMIDs ----
    esearch_params = {
        "db": "pubmed",
        "term": keywords,
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
        "datetype": "pdat",
        "mindate": date_from,
        "maxdate": date_to,
    }
    if config.NCBI_API_KEY:
        esearch_params["api_key"] = config.NCBI_API_KEY
    if config.NCBI_EMAIL:
        esearch_params["tool"] = "biblio"
        esearch_params["email"] = config.NCBI_EMAIL

    logger.info(f"PubMed esearch: term={keywords} mindate={esearch_params['mindate']} maxdate={esearch_params['maxdate']}")

    resp = requests.get(ESEARCH_URL, params=esearch_params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    esearch_result = data.get("esearchresult", {})

    # Check for API errors
    error_list = esearch_result.get("errorlist", {})
    if error_list:
        phrase_errors = error_list.get("phrasesnotfound", [])
        field_errors = error_list.get("fieldsnotfound", [])
        if phrase_errors:
            logger.warning(f"PubMed: phrases not found: {phrase_errors}")
        if field_errors:
            logger.warning(f"PubMed: fields not found: {field_errors}")

    id_list = esearch_result.get("idlist", [])
    total_count = esearch_result.get("count", "0")
    logger.info(f"PubMed: {total_count} total matches, {len(id_list)} IDs retrieved")

    if not id_list:
        return []

    # ---- Step 2: efetch to get article details ----
    articles = []
    batch_size = 20
    delay = 0.11 if config.NCBI_API_KEY else 0.34  # 10 req/s with key, 3 req/s without

    for i in range(0, len(id_list), batch_size):
        batch = id_list[i:i + batch_size]

        efetch_params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "xml",
            "retmode": "xml",
        }
        if config.NCBI_API_KEY:
            efetch_params["api_key"] = config.NCBI_API_KEY
        if config.NCBI_EMAIL:
            efetch_params["tool"] = "biblio"
            efetch_params["email"] = config.NCBI_EMAIL

        resp2 = requests.get(EFETCH_URL, params=efetch_params, timeout=30)
        resp2.raise_for_status()

        try:
            root = ET.fromstring(resp2.text)
        except ET.ParseError as e:
            logger.error(f"PubMed XML parse error: {e}")
            continue

        for pa in root.findall("PubmedArticle"):
            try:
                article = _parse_xml_article(pa)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"PubMed: error parsing article: {e}")

        if i + batch_size < len(id_list):
            time.sleep(delay)

    logger.info(f"PubMed: {len(articles)} articles parsed successfully")
    return articles


def _get_text(element, path: str, default: str = "") -> str:
    """Get text from XML element at path, or default."""
    el = element.find(path)
    return (el.text or default) if el is not None else default


def _parse_xml_article(pa) -> Article | None:
    """Parse a PubmedArticle XML element into an Article."""
    mc = pa.find("MedlineCitation")
    if mc is None:
        return None

    article_el = mc.find("Article")
    if article_el is None:
        return None

    # Title
    title = _get_text(article_el, "ArticleTitle")
    if not title:
        return None

    # PMID
    pmid = _get_text(mc, "PMID")

    # Authors
    authors = []
    author_list = article_el.find("AuthorList")
    if author_list is not None:
        for author in author_list.findall("Author"):
            last = _get_text(author, "LastName")
            fore = _get_text(author, "ForeName")
            if last:
                authors.append(f"{last} {fore}".strip())

    # Journal
    journal_el = article_el.find("Journal")
    journal = ""
    year = None
    if journal_el is not None:
        journal = _get_text(journal_el, "Title") or _get_text(journal_el, "ISOAbbreviation")
        # Year
        pub_date = journal_el.find("JournalIssue/PubDate")
        if pub_date is not None:
            year_str = _get_text(pub_date, "Year")
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass
            if not year:
                medline_date = _get_text(pub_date, "MedlineDate")
                if medline_date and len(medline_date) >= 4:
                    try:
                        year = int(medline_date[:4])
                    except ValueError:
                        pass

    # Abstract
    abstract_el = article_el.find("Abstract")
    abstract = None
    if abstract_el is not None:
        parts = []
        for at in abstract_el.findall("AbstractText"):
            full_text = ET.tostring(at, encoding="unicode", method="text").strip()
            if full_text:
                parts.append(full_text)
            elif at.text:
                parts.append(at.text)
        abstract = " ".join(parts) if parts else None

    # DOI
    doi = None
    for eid in article_el.findall("ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = eid.text
            break
    if not doi:
        pd = pa.find("PubmedData")
        if pd is not None:
            for aid in pd.findall("ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break

    # Keywords (MeSH + author keywords)
    keywords_list = []
    for mesh in mc.findall("MeshHeadingList/MeshHeading/DescriptorName"):
        if mesh.text:
            keywords_list.append(mesh.text)
    for kw_list in mc.findall("KeywordList"):
        for kw in kw_list.findall("Keyword"):
            if kw.text:
                keywords_list.append(kw.text)

    return Article(
        title=title,
        authors=authors,
        doi=doi,
        journal=journal,
        year=year,
        abstract=abstract,
        keywords=keywords_list[:20],
        citation_count=0,
        source="pubmed",
        pmid=pmid or None,
    )
