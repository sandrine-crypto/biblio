"""Déduplication des articles par DOI et similarité de titre."""

import logging
import re

from rapidfuzz import fuzz

import config
from models import Article

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalise un titre pour la comparaison."""
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title


def deduplicate_articles(articles: list[Article]) -> tuple[list[Article], int, list[str]]:
    """Déduplique les articles par DOI puis par similarité de titre.

    Returns:
        Tuple (articles_dédupliqués, nombre_doublons, log_doublons)
    """
    duplicate_log = []
    total_before = len(articles)

    # Phase 1: Déduplication par DOI exact
    doi_groups: dict[str, list[Article]] = {}
    no_doi: list[Article] = []

    for article in articles:
        if article.doi:
            doi_key = article.doi.lower().strip()
            if doi_key not in doi_groups:
                doi_groups[doi_key] = []
            doi_groups[doi_key].append(article)
        else:
            no_doi.append(article)

    deduplicated = []
    doi_dupes = 0
    for doi, group in doi_groups.items():
        if len(group) > 1:
            # Garder le plus complet
            group.sort(key=lambda a: a.completeness_score(), reverse=True)
            deduplicated.append(group[0])
            for dup in group[1:]:
                doi_dupes += 1
                duplicate_log.append(
                    f"DOI doublon: '{dup.title}' ({dup.source}) supprimé, "
                    f"gardé depuis {group[0].source}"
                )
        else:
            deduplicated.append(group[0])

    # Phase 2: Déduplication par similarité de titre (pour articles sans DOI + restants)
    all_candidates = deduplicated + no_doi
    kept = []
    removed_indices = set()
    title_dupes = 0

    for i, article_i in enumerate(all_candidates):
        if i in removed_indices:
            continue

        norm_i = normalize_title(article_i.title)
        if not norm_i:
            kept.append(article_i)
            continue

        for j in range(i + 1, len(all_candidates)):
            if j in removed_indices:
                continue

            norm_j = normalize_title(all_candidates[j].title)
            if not norm_j:
                continue

            score = fuzz.token_sort_ratio(norm_i, norm_j)
            if score >= config.DEDUP_TITLE_THRESHOLD:
                # Garder le plus complet
                if article_i.completeness_score() >= all_candidates[j].completeness_score():
                    removed_indices.add(j)
                    title_dupes += 1
                    duplicate_log.append(
                        f"Titre similaire ({score}%): '{all_candidates[j].title}' "
                        f"({all_candidates[j].source}) supprimé, "
                        f"gardé '{article_i.title}' ({article_i.source})"
                    )
                else:
                    removed_indices.add(i)
                    title_dupes += 1
                    duplicate_log.append(
                        f"Titre similaire ({score}%): '{article_i.title}' "
                        f"({article_i.source}) supprimé, "
                        f"gardé '{all_candidates[j].title}' ({all_candidates[j].source})"
                    )
                    break

        if i not in removed_indices:
            kept.append(article_i)

    total_dupes = doi_dupes + title_dupes
    logger.info(
        f"Déduplication: {total_before} → {len(kept)} articles "
        f"({doi_dupes} doublons DOI, {title_dupes} doublons titre)"
    )

    return kept, total_dupes, duplicate_log
