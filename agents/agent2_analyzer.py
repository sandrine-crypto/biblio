"""Agent 2 — Scientific Researcher: Analysis and synthesis via Anthropic API."""

import json
import logging
import os

import anthropic

import config
from models import Article

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "fr": """Tu es un chercheur scientifique de niveau Nature/Science. Tu produis des revues de litterature rigoureuses et exhaustives.

REGLES IMPERATIVES :
1. Toute affirmation doit etre tracee vers un article source. Cite avec un lien hypertexte Markdown vers l'URL de l'article : [Auteur et al., Annee](URL). Si pas d'URL, utilise [DOI: xxx].
2. N'invente AUCUNE information qui n'est pas dans le corpus fourni.
3. Niveau de langage : revue Nature/Science, precis et academique.
4. Ecris en francais sauf si les termes techniques n'ont pas d'equivalent francais courant.
5. Chaque donnee chiffree (pourcentage, p-value, effectif, odds ratio, etc.) DOIT etre exactement celle de l'article cite. Aucune approximation.""",

    "en": """You are a Nature/Science-level scientific researcher. You produce rigorous and exhaustive literature reviews.

MANDATORY RULES:
1. Every claim must be traced to a source article. Cite with a Markdown hyperlink to the article URL: [Author et al., Year](URL). If no URL, use [DOI: xxx].
2. Do NOT invent ANY information not in the provided corpus.
3. Language level: Nature/Science review, precise and academic.
4. Write in English throughout.
5. Every numerical data point (percentage, p-value, sample size, odds ratio, etc.) MUST be exactly as reported in the cited article. No approximation.""",
}

ANALYSIS_PROMPTS = {
    "fr": """Analyse le corpus d'articles scientifiques suivant et produis un rapport structure.

STRUCTURE OBLIGATOIRE DU RAPPORT :

## 1. Resume executif
(250 mots maximum. Synthese des principales decouvertes et tendances.)

## 2. Etat de l'art
(Structure par sous-thematiques que tu identifies automatiquement dans le corpus. Chaque sous-section doit citer les articles pertinents avec leur DOI.)

## 3. Tendances temporelles
(Evolution de la litterature sur la periode couverte. Quels sujets emergent, lesquels declinent ?)

## 4. Gaps et controverses
(Lacunes identifiees dans la litterature. Points de debat ou resultats contradictoires entre etudes.)

## 5. Articles cles
(Top 10 des articles les plus pertinents avec justification. Format :
- [**Titre**](URL) — Auteurs (Annee). Journal. DOI: xxx
  Justification de la selection.)

## 6. Bibliographie Vancouver
(Tous les articles cites dans le rapport, numerotes au format Vancouver. Chaque reference doit inclure un lien hypertexte vers l'article : [N] Auteurs. Titre. Journal. Annee. [Lien](URL))

---

CORPUS D'ARTICLES :
{corpus}""",

    "en": """Analyze the following scientific article corpus and produce a structured report.

MANDATORY REPORT STRUCTURE:

## 1. Executive Summary
(250 words maximum. Synthesis of key findings and trends.)

## 2. State of the Art
(Structured by sub-topics you automatically identify in the corpus. Each sub-section must cite relevant articles with their DOI.)

## 3. Temporal Trends
(Evolution of the literature over the covered period. Which topics are emerging, which are declining?)

## 4. Gaps and Controversies
(Identified gaps in the literature. Points of debate or contradictory results between studies.)

## 5. Key Articles
(Top 10 most relevant articles with justification. Format:
- [**Title**](URL) — Authors (Year). Journal. DOI: xxx
  Justification for selection.)

## 6. Vancouver Bibliography
(All articles cited in the report, numbered in Vancouver format. Each reference must include a hyperlink to the article: [N] Authors. Title. Journal. Year. [Link](URL))

---

ARTICLE CORPUS:
{corpus}""",
}

MAP_PROMPTS = {
    "fr": """Analyse ce sous-ensemble du corpus scientifique. Identifie :
1. Les themes principaux et sous-themes
2. Les tendances et evolutions temporelles
3. Les gaps et controverses
4. Les articles les plus importants (avec DOI)

Cite systematiquement les DOI. N'invente rien.

SOUS-ENSEMBLE :
{corpus}""",

    "en": """Analyze this subset of the scientific corpus. Identify:
1. Main themes and sub-themes
2. Trends and temporal evolution
3. Gaps and controversies
4. Most important articles (with DOI)

Systematically cite DOIs. Do not invent anything.

SUBSET:
{corpus}""",
}

REDUCE_PROMPTS = {
    "fr": """Tu recois {n} syntheses partielles d'un corpus scientifique plus large.
Consolide-les en UN SEUL rapport unifie avec la structure suivante :

## 1. Resume executif
(250 mots maximum)

## 2. Etat de l'art
(Structure par sous-thematiques identifiees. Chaque sous-section cite les DOI pertinents.)

## 3. Tendances temporelles
(Evolution de la litterature sur la periode couverte.)

## 4. Gaps et controverses
(Lacunes et debats identifies.)

## 5. Articles cles
(Top 10, avec DOI et justification.)

## 6. Bibliographie Vancouver
(Tous les articles cites, numerotes.)

Elimine les redondances entre syntheses partielles. Cite les DOI. N'invente rien.

SYNTHESES PARTIELLES :
{partial_syntheses}""",

    "en": """You receive {n} partial syntheses from a larger scientific corpus.
Consolidate them into ONE unified report with the following structure:

## 1. Executive Summary
(250 words maximum)

## 2. State of the Art
(Structured by identified sub-topics. Each sub-section cites relevant DOIs.)

## 3. Temporal Trends
(Evolution of the literature over the covered period.)

## 4. Gaps and Controversies
(Identified gaps and debates.)

## 5. Key Articles
(Top 10, with DOI and justification.)

## 6. Vancouver Bibliography
(All cited articles, numbered.)

Eliminate redundancies between partial syntheses. Cite DOIs. Do not invent anything.

PARTIAL SYNTHESES:
{partial_syntheses}""",
}


def _estimate_tokens(text: str) -> int:
    return len(text) // config.TOKEN_ESTIMATE_DIVISOR


def _format_corpus(articles: list[Article]) -> str:
    parts = []
    for i, article in enumerate(articles, 1):
        lines = [f"### Article {i}"]
        lines.append(f"**Titre:** {article.title}")
        if article.url:
            lines.append(f"**URL:** {article.url}")
        if article.doi:
            lines.append(f"**DOI:** {article.doi}")
        if article.authors:
            lines.append(f"**Auteurs:** {', '.join(article.authors[:10])}")
        if article.journal:
            lines.append(f"**Journal:** {article.journal}")
        if article.year:
            lines.append(f"**Annee:** {article.year}")
        if article.abstract:
            lines.append(f"**Resume:** {article.abstract}")
        if article.keywords:
            lines.append(f"**Mots-cles:** {', '.join(article.keywords)}")
        if article.citation_count:
            lines.append(f"**Citations:** {article.citation_count}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def _chunk_articles(articles: list[Article], max_tokens: int) -> list[list[Article]]:
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
    lang: str = "fr",
) -> tuple[str, list[dict]]:
    """Analyze the corpus and produce a scientific report.

    Args:
        articles: Deduplicated article list
        progress_callback: Optional function (message: str)
        lang: Output language ('fr' or 'en')

    Returns:
        Tuple (report_markdown, cited_article_metadata)
    """
    if not config.ANTHROPIC_API_KEY:
        msg = "⚠️ ANTHROPIC_API_KEY not configured." if lang == "en" else "⚠️ ANTHROPIC_API_KEY non configuree."
        logger.warning(msg)
        if progress_callback:
            progress_callback(msg)
        return _generate_fallback_report(articles, lang), _extract_cited_metadata(articles)

    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    corpus_text = _format_corpus(articles)
    estimated_tokens = _estimate_tokens(corpus_text)

    log_progress(f"📝 Corpus: {len(articles)} articles, ~{estimated_tokens:,} tokens")

    system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["fr"])

    if estimated_tokens <= config.MAX_TOKENS_SINGLE_CALL:
        log_progress("📤 Sending full corpus to Claude...")
        report = _single_pass_analysis(client, corpus_text, system_prompt, lang, log_progress)
    else:
        log_progress("📦 Corpus too large, activating Map-Reduce...")
        report = _map_reduce_analysis(client, articles, system_prompt, lang, log_progress)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(config.OUTPUT_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    cited_metadata = _extract_cited_metadata(articles)
    meta_path = os.path.join(config.OUTPUT_DIR, "cited_articles.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(cited_metadata, f, ensure_ascii=False, indent=2)

    log_progress("✅ Analysis report generated")
    return report, cited_metadata


def _single_pass_analysis(client, corpus_text: str, system_prompt: str, lang: str, log_progress) -> str:
    prompt = ANALYSIS_PROMPTS.get(lang, ANALYSIS_PROMPTS["fr"]).format(corpus=corpus_text)

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _map_reduce_analysis(client, articles: list[Article], system_prompt: str, lang: str, log_progress) -> str:
    chunks = _chunk_articles(articles, config.CHUNK_TOKEN_SIZE)
    log_progress(f"📦 Corpus split into {len(chunks)} chunks")

    map_template = MAP_PROMPTS.get(lang, MAP_PROMPTS["fr"])

    partial_syntheses = []
    for i, chunk in enumerate(chunks, 1):
        log_progress(f"🔄 Map: analyzing chunk {i}/{len(chunks)} ({len(chunk)} articles)...")
        chunk_text = _format_corpus(chunk)
        prompt = map_template.format(corpus=chunk_text)

        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        partial_syntheses.append(response.content[0].text)

    log_progress("🔄 Reduce: consolidating partial syntheses...")
    combined = "\n\n===== PARTIAL SYNTHESIS =====\n\n".join(
        f"### Chunk {i+1}\n{s}" for i, s in enumerate(partial_syntheses)
    )
    reduce_template = REDUCE_PROMPTS.get(lang, REDUCE_PROMPTS["fr"])
    prompt = reduce_template.format(n=len(partial_syntheses), partial_syntheses=combined)

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _generate_fallback_report(articles: list[Article], lang: str = "fr") -> str:
    if lang == "en":
        lines = ["# Literature Report (degraded mode — no LLM analysis)\n"]
        lines.append(f"**Number of articles:** {len(articles)}\n")
    else:
        lines = ["# Rapport bibliographique (mode degrade — sans analyse LLM)\n"]
        lines.append(f"**Nombre d'articles:** {len(articles)}\n")

    if articles:
        years = [a.year for a in articles if a.year]
        if years:
            if lang == "en":
                lines.append(f"**Period covered:** {min(years)}-{max(years)}\n")
            else:
                lines.append(f"**Periode couverte:** {min(years)}-{max(years)}\n")

        journals = {}
        for a in articles:
            if a.journal:
                journals[a.journal] = journals.get(a.journal, 0) + 1

        if journals:
            if lang == "en":
                lines.append("## Most represented journals\n")
            else:
                lines.append("## Journaux les plus representes\n")
            for j, c in sorted(journals.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- {j}: {c} articles")

        if lang == "en":
            lines.append("\n## Article list\n")
        else:
            lines.append("\n## Liste des articles\n")
        for i, a in enumerate(articles[:50], 1):
            doi_str = f" DOI: {a.doi}" if a.doi else ""
            lines.append(f"{i}. {a.title} — {', '.join(a.authors[:3])} ({a.year}).{doi_str}")

    return "\n".join(lines)


def _extract_cited_metadata(articles: list[Article]) -> list[dict]:
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
