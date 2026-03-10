"""Agent 1 — Documentaliste : Collecte multi-sources et déduplication."""

import json
import logging
import os

import config
from models import Article, CollectionReport, articles_to_json
from sources.pubmed import search_pubmed
from sources.semantic_scholar import search_semantic_scholar
from sources.europe_pmc import search_europe_pmc
from sources.google_scholar import search_google_scholar
from utils.deduplication import deduplicate_articles

logger = logging.getLogger(__name__)

SOURCE_FUNCTIONS = {
    "pubmed": search_pubmed,
    "semantic_scholar": search_semantic_scholar,
    "europe_pmc": search_europe_pmc,
    "google_scholar": search_google_scholar,
}


def run_collection(
    keywords: str,
    date_from: str,
    date_to: str,
    sources_enabled: list[str] | None = None,
    max_results: int = 50,
    progress_callback=None,
    semantic_mode: bool = False,
    llm_provider: str | None = None,
    lang: str = "fr",
) -> tuple[list[Article], CollectionReport]:
    """Exécute la collecte multi-sources avec déduplication.

    Args:
        keywords: Termes de recherche
        date_from: Date de début (YYYY/MM/DD)
        date_to: Date de fin (YYYY/MM/DD)
        sources_enabled: Liste des sources à utiliser (None = toutes)
        max_results: Nombre max de résultats par source
        progress_callback: Fonction optionnelle (message: str) pour le suivi
        semantic_mode: Si True, transformer la requête sémantique en booléenne via LLM
        llm_provider: Fournisseur LLM pour la transformation (requis si semantic_mode=True)
        lang: Langue pour les prompts LLM

    Returns:
        Tuple (articles_dédupliqués, rapport_collecte)
    """
    # Normalize multi-line keywords to single line (preserve quoted expressions)
    keywords = " ".join(keywords.splitlines()).strip()

    # Semantic → Boolean transformation
    if semantic_mode and llm_provider:
        from utils.query_transformer import transform_query

        def log_progress(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        log_progress("🧠 Transformation sémantique → booléenne..." if lang == "fr"
                     else "🧠 Semantic → boolean query transformation...")
        try:
            keywords = transform_query(keywords, llm_provider, lang)
            log_progress(f"✅ Requête booléenne : `{keywords}`" if lang == "fr"
                         else f"✅ Boolean query: `{keywords}`")
        except Exception as e:
            logger.error(f"Query transformation failed: {e}")
            log_progress(f"⚠️ Transformation échouée, requête originale conservée — {e}" if lang == "fr"
                         else f"⚠️ Transformation failed, using original query — {e}")

    if sources_enabled is None:
        sources_enabled = list(SOURCE_FUNCTIONS.keys())

    report = CollectionReport()
    all_articles: list[Article] = []

    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    # Collecte par source
    for source_name in sources_enabled:
        if source_name not in SOURCE_FUNCTIONS:
            logger.warning(f"Source inconnue: {source_name}")
            continue

        log_progress(f"🔍 Recherche {source_name}...")
        search_fn = SOURCE_FUNCTIONS[source_name]

        try:
            results = search_fn(keywords, date_from, date_to, max_results=max_results)
            report.per_source[source_name] = len(results)
            all_articles.extend(results)
            log_progress(f"✅ {source_name}: {len(results)} articles trouvés")
        except Exception as e:
            logger.error(f"Erreur {source_name}: {e}")
            report.per_source[source_name] = 0
            log_progress(f"⚠️ {source_name}: erreur - {e}")

    report.total_collected = len(all_articles)
    log_progress(f"📊 Total collecté: {report.total_collected} articles")

    # Déduplication
    log_progress("🔄 Déduplication en cours...")
    deduplicated, n_dupes, dup_log = deduplicate_articles(all_articles)

    report.duplicates_removed = n_dupes
    report.duplicate_log = dup_log
    report.final_count = len(deduplicated)

    log_progress(
        f"✅ Déduplication terminée: {report.duplicates_removed} doublons supprimés, "
        f"{report.final_count} articles uniques"
    )

    # Sauvegarde JSON
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    corpus_path = os.path.join(config.OUTPUT_DIR, "corpus.json")
    with open(corpus_path, "w", encoding="utf-8") as f:
        f.write(articles_to_json(deduplicated))

    report_path = os.path.join(config.OUTPUT_DIR, "collection_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    return deduplicated, report
