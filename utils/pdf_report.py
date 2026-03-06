"""Génération du rapport HTML infographique téléchargeable."""

import base64
import logging
import os
import re
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
import markdown as md

import config
from models import Article, EditorReport

logger = logging.getLogger(__name__)

FIGURE_CAPTIONS = {
    "timeline.png": "Volume de publications par année",
    "top_journals.png": "Top 15 journaux par nombre de publications",
    "wordcloud.png": "Nuage de mots des abstracts",
    "cocitation_network.png": "Réseau de co-citations (mots-clés partagés)",
    "theme_heatmap.png": "Heatmap des sous-thématiques par année",
}


def _markdown_to_html(markdown_text: str) -> str:
    """Convertit le Markdown en HTML via la bibliothèque markdown."""
    return md.markdown(
        markdown_text,
        extensions=["extra", "smarty", "sane_lists", "toc"],
        output_format="html",
    )


def _encode_figure_b64(fig_path: str) -> str | None:
    """Encode une image en base64 pour l'intégration HTML."""
    if not os.path.exists(fig_path):
        return None
    with open(fig_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_html_report(
    report_markdown: str,
    articles: list[Article],
    editor_report: EditorReport,
    keywords: str,
    date_from: str,
    date_to: str,
) -> str:
    """Génère le rapport HTML infographique standalone.

    Returns:
        Contenu HTML complet (string) prêt à télécharger.
    """
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("report.html")

    report_html = _markdown_to_html(report_markdown)

    # Figures en base64
    figures_b64 = []
    for fig_path in editor_report.figures_generated:
        b64 = _encode_figure_b64(fig_path)
        if b64:
            fname = os.path.basename(fig_path)
            caption = FIGURE_CAPTIONS.get(fname, fname)
            figures_b64.append({"data": b64, "caption": caption})

    # Sources
    sources_list = set(a.source for a in articles)
    sources_str = ", ".join(sorted(sources_list))

    # Période effective
    years = [a.year for a in articles if a.year]
    year_range = f"{min(years)}-{max(years)}" if years else ""

    # Articles data pour le tableau
    articles_data = []
    for a in articles:
        articles_data.append({
            "title": a.title,
            "url": a.url,
            "authors": ", ".join(a.authors[:3]) + ("..." if len(a.authors) > 3 else ""),
            "journal": a.journal,
            "year": a.year,
            "citations": a.citation_count,
        })

    # Vérifications
    verifications = [
        {
            "claim": v.claim,
            "verified": v.verified,
            "confidence": v.confidence,
            "correction": v.correction,
            "source": v.source,
        }
        for v in editor_report.verifications
    ]

    html_content = template.render(
        title="Rapport de Recherche Bibliographique Scientifique",
        keywords=keywords,
        date_from=date_from,
        date_to=date_to,
        article_count=len(articles),
        sources=sources_str,
        report_date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        confidence_score=editor_report.confidence_score,
        year_range=year_range,
        report_html=report_html,
        figures_b64=figures_b64,
        articles_data=articles_data,
        verifications=verifications,
    )

    # Sauvegarde locale
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(config.OUTPUT_DIR, "rapport_bibliographique.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"HTML report generated: {output_path}")
    return html_content


# Keep backward-compatible alias
def generate_pdf(
    report_markdown: str,
    articles: list[Article],
    editor_report: EditorReport,
    keywords: str,
    date_from: str,
    date_to: str,
    output_path: str | None = None,
) -> str | None:
    """Backward-compatible wrapper — now generates HTML."""
    html = generate_html_report(
        report_markdown, articles, editor_report, keywords, date_from, date_to
    )
    path = os.path.join(config.OUTPUT_DIR, "rapport_bibliographique.html")
    return path if os.path.exists(path) else None
