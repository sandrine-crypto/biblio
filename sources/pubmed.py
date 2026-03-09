"""Client PubMed via Biopython Entrez."""

import logging
import time

from Bio import Entrez

import config
from models import Article

logger = logging.getLogger(__name__)


def search_pubmed(keywords: str, date_from: str, date_to: str, max_results: int | None = None) -> list[Article]:
    """Recherche PubMed et retourne une liste d'Articles.

    Args:
        keywords: Termes de recherche
        date_from: Date de début (YYYY/MM/DD)
        date_to: Date de fin (YYYY/MM/DD)
        max_results: Nombre maximum de résultats
    """
    if max_results is None:
        max_results = config.MAX_RESULTS_PER_SOURCE
    Entrez.email = config.NCBI_EMAIL
    if config.NCBI_API_KEY:
        Entrez.api_key = config.NCBI_API_KEY
    articles = []

    try:
        logger.info(f"PubMed search: {keywords} [{date_from} - {date_to}]")

        handle = Entrez.esearch(
            db="pubmed",
            term=keywords,
            retmax=max_results,
            sort="relevance",
            datetype="pdat",
            mindate=date_from,
            maxdate=date_to,
        )
        results = Entrez.read(handle)
        handle.close()

        id_list = results.get("IdList", [])
        if not id_list:
            logger.info("PubMed: aucun résultat trouvé")
            return articles

        logger.info(f"PubMed: {len(id_list)} articles trouvés")

        # Fetch details in batches of 20
        batch_size = 20
        for i in range(0, len(id_list), batch_size):
            batch = id_list[i:i + batch_size]
            handle = Entrez.efetch(db="pubmed", id=",".join(batch), rettype="xml", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            for record in records.get("PubmedArticle", []):
                try:
                    article = _parse_pubmed_record(record)
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"PubMed: erreur parsing article: {e}")

            if i + batch_size < len(id_list):
                time.sleep(0.34)  # Respect rate limit (3 req/s)

    except Exception as e:
        logger.error(f"PubMed search error: {e}")

    return articles


def _parse_pubmed_record(record: dict) -> Article:
    """Parse un enregistrement PubMed en Article."""
    medline = record.get("MedlineCitation", {})
    article_data = medline.get("Article", {})

    # Title
    title = str(article_data.get("ArticleTitle", ""))

    # Authors
    authors = []
    author_list = article_data.get("AuthorList", [])
    for author in author_list:
        last = author.get("LastName", "")
        fore = author.get("ForeName", "")
        if last:
            authors.append(f"{last} {fore}".strip())

    # Journal
    journal_info = article_data.get("Journal", {})
    journal = str(journal_info.get("Title", "") or journal_info.get("ISOAbbreviation", ""))

    # Year
    year = None
    pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
    year_str = pub_date.get("Year", "")
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            pass
    if not year:
        medline_date = pub_date.get("MedlineDate", "")
        if medline_date and len(medline_date) >= 4:
            try:
                year = int(medline_date[:4])
            except ValueError:
                pass

    # Abstract
    abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join(str(part) for part in abstract_parts) if abstract_parts else None

    # DOI
    doi = None
    id_list = article_data.get("ELocationID", [])
    for eid in id_list:
        if eid.attributes.get("EIdType", "") == "doi":
            doi = str(eid)
            break
    if not doi:
        article_ids = record.get("PubmedData", {}).get("ArticleIdList", [])
        for aid in article_ids:
            if aid.attributes.get("IdType", "") == "doi":
                doi = str(aid)
                break

    # PMID
    pmid = str(medline.get("PMID", "")) or None

    # Keywords
    keywords_list = []
    mesh_headings = medline.get("MeshHeadingList", [])
    for mesh in mesh_headings:
        descriptor = mesh.get("DescriptorName", "")
        if descriptor:
            keywords_list.append(str(descriptor))
    kw_list = medline.get("KeywordList", [])
    for kw_group in kw_list:
        for kw in kw_group:
            keywords_list.append(str(kw))

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
        pmid=pmid,
    )
