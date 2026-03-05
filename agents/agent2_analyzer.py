"""Agent 2 — Chercheur scientifique : Analyse et synthèse via API Anthropic."""

import json
import logging
import os

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, OUTPUT_DIR, TOKEN_ESTIMATE_DIVISOR, MAX_TOKENS_SINGLE_CALL, CHUNK_TOKEN_SIZE
from models import Article

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un chercheur scientifique de niveau Nature/Science. Tu produis des revues de littérature rigoureuses et exhaustives.

RÈGLES IMPÉRATIVES :
1. Toute affirmation doit être tracée vers un DOI source. Cite sous la forme [DOI: xxx].
2. N'invente AUCUNE information qui n'est pas dans le corpus fourni.
3. Niveau de langage : revue Nature/Science, précis et académique.
4. Écris en français sauf si les termes techniques n'ont pas d'équivalent français courant."""

ANALYSIS_PROMPT = """Analyse le corpus d'articles scientifiques suivant et produis un rapport structuré.

STRUCTURE OBLIGATOIRE DU RAPPORT :

## 1. Résumé exécutif
(250 mots maximum. Synthèse des principales découvertes et tendances.)

## 2. État de l'art
(Structuré par sous-thématiques que tu identifies automatiquement dans le corpus. Chaque sous-section doit citer les articles pertinents avec leur DOI.)

## 3. Tendances temporelles
(Évolution de la littérature sur la période couverte. Quels sujets émergent, lesquels déclinent ?)

## 4. Gaps et controverses
(Lacunes identifiées dans la littérature. Points de débat ou résultats contradictoires entre études.)

## 5. Articles clés
(Top 10 des articles les plus pertinents avec justification. Format :
- **Titre** — Auteurs (Année). Journal. DOI: xxx
  Justification de la sélection.)

## 6. Bibliographie Vancouver
(Tous les articles cités dans le rapport, numérotés au format Vancouver.)

---

CORPUS D'ARTICLES :
{corpus}"""

MAP_PROMPT = """Analyse ce sous-ensemble du corpus scientifique. Identifie :
1. Les thèmes principaux et sous-thèmes
2. Les tendances et évolutions temporelles
3. Les gaps et controverses
4. Les articles les plus importants (avec DOI)

Cite systématiquement les DOI. N'invente rien.

SOUS-ENSEMBLE :
{corpus}"""

REDUCE_PROMPT = """Tu reçois {n} synthèses partielles d'un corpus scientifique plus large.
Consolide-les en UN SEUL rapport unifié avec la structure suivante :

## 1. Résumé exécutif
(250 mots maximum)

## 2. État de l'art
(Structuré par sous-thématiques identifiées. Chaque sous-section cite les DOI pertinents.)

## 3. Tendances temporelles
(Évolution de la littérature sur la période couverte.)

## 4. Gaps et controverses
(Lacunes et débats identifiés.)

## 5. Articles clés
(Top 10, avec DOI et justification.)

## 6. Bibliographie Vancouver
(Tous les articles cités, numérotés.)

Élimine les redondances entre synthèses partielles. Cite les DOI. N'invente rien.

SYNTHÈSES PARTIELLES :
{partial_syntheses}"""


def _estimate_tokens(text: str) -> int:
    """Estime le nombre de tokens approximatif."""
    return len(text) // TOKEN_ESTIMATE_DIVISOR


def _format_corpus(articles: list[Article]) -> str:
    """Formate le corpus pour l'envoi à l'API."""
    parts = []
    for i, article in enumerate(articles, 1):
        lines = [f"### Article {i}"]
        lines.append(f"**Titre:** {article.title}")
        if article.doi:
            lines.append(f"**DOI:** {article.doi}")
        if article.authors:
            lines.append(f"**Auteurs:** {', '.join(article.authors[:10])}")
        if article.journal:
            lines.append(f"**Journal:** {article.journal}")
        if article.year:
            lines.append(f"**Année:** {article.year}")
        if article.abstract:
            lines.append(f"**Résumé:** {article.abstract}")
        if article.keywords:
            lines.append(f"**Mots-clés:** {', '.join(article.keywords)}")
        if article.citation_count:
            lines.append(f"**Citations:** {article.citation_count}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def _chunk_articles(articles: list[Article], max_tokens: int) -> list[list[Article]]:
    """Découpe les articles en chunks sans couper un article."""
    chunks = []
    current_chunk = []
    current_tokens = 0

    for article in articles:
        article_text = _format_corpus([article])
        article_tokens = _estimate_tokens(article_text)

        if current_tokens + article_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(article)
        current_tokens += article_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def run_analysis(
    articles: list[Article],
    progress_callback=None,
) -> tuple[str, list[dict]]:
    """Analyse le corpus et produit un rapport scientifique.

    Args:
        articles: Liste d'articles dédupliqués
        progress_callback: Fonction optionnelle (message: str)

    Returns:
        Tuple (rapport_markdown, métadonnées_articles_cités)
    """
    if not ANTHROPIC_API_KEY:
        msg = "⚠️ ANTHROPIC_API_KEY non configurée. Impossible de générer l'analyse."
        logger.warning(msg)
        if progress_callback:
            progress_callback(msg)
        return _generate_fallback_report(articles), _extract_cited_metadata(articles)

    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    corpus_text = _format_corpus(articles)
    estimated_tokens = _estimate_tokens(corpus_text)

    log_progress(f"📝 Corpus: {len(articles)} articles, ~{estimated_tokens:,} tokens estimés")

    if estimated_tokens <= MAX_TOKENS_SINGLE_CALL:
        # Traitement en une seule passe
        log_progress("📤 Envoi du corpus complet à Claude...")
        report = _single_pass_analysis(client, corpus_text, log_progress)
    else:
        # Map-Reduce
        log_progress(f"📦 Corpus trop grand, activation du Map-Reduce...")
        report = _map_reduce_analysis(client, articles, log_progress)

    # Sauvegarde
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    cited_metadata = _extract_cited_metadata(articles)
    meta_path = os.path.join(OUTPUT_DIR, "cited_articles.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(cited_metadata, f, ensure_ascii=False, indent=2)

    log_progress("✅ Rapport d'analyse généré")
    return report, cited_metadata


def _single_pass_analysis(client, corpus_text: str, log_progress) -> str:
    """Analyse en une seule passe."""
    prompt = ANALYSIS_PROMPT.format(corpus=corpus_text)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _map_reduce_analysis(client, articles: list[Article], log_progress) -> str:
    """Analyse Map-Reduce pour grands corpus."""
    chunks = _chunk_articles(articles, CHUNK_TOKEN_SIZE)
    log_progress(f"📦 Corpus découpé en {len(chunks)} chunks")

    # Phase Map
    partial_syntheses = []
    for i, chunk in enumerate(chunks, 1):
        log_progress(f"🔄 Map: analyse du chunk {i}/{len(chunks)} ({len(chunk)} articles)...")
        chunk_text = _format_corpus(chunk)
        prompt = MAP_PROMPT.format(corpus=chunk_text)

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        partial_syntheses.append(response.content[0].text)

    # Phase Reduce
    log_progress("🔄 Reduce: consolidation des synthèses partielles...")
    combined = "\n\n===== SYNTHÈSE PARTIELLE =====\n\n".join(
        f"### Chunk {i+1}\n{s}" for i, s in enumerate(partial_syntheses)
    )
    prompt = REDUCE_PROMPT.format(n=len(partial_syntheses), partial_syntheses=combined)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _generate_fallback_report(articles: list[Article]) -> str:
    """Génère un rapport basique sans LLM."""
    lines = ["# Rapport bibliographique (mode dégradé — sans analyse LLM)\n"]
    lines.append(f"**Nombre d'articles:** {len(articles)}\n")

    if articles:
        years = [a.year for a in articles if a.year]
        if years:
            lines.append(f"**Période couverte:** {min(years)}-{max(years)}\n")

        journals = {}
        for a in articles:
            if a.journal:
                journals[a.journal] = journals.get(a.journal, 0) + 1

        if journals:
            lines.append("## Journaux les plus représentés\n")
            for j, c in sorted(journals.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- {j}: {c} articles")

        lines.append("\n## Liste des articles\n")
        for i, a in enumerate(articles[:50], 1):
            doi_str = f" DOI: {a.doi}" if a.doi else ""
            lines.append(f"{i}. {a.title} — {', '.join(a.authors[:3])} ({a.year}).{doi_str}")

    return "\n".join(lines)


def _extract_cited_metadata(articles: list[Article]) -> list[dict]:
    """Extrait les métadonnées des articles pour le fichier JSON."""
    return [
        {
            "title": a.title,
            "authors": a.authors,
            "doi": a.doi,
            "journal": a.journal,
            "year": a.year,
            "citation_count": a.citation_count,
        }
        for a in articles
    ]
