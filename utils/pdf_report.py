"""Génération du rapport PDF via WeasyPrint."""

import logging
import os
import re
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from config import OUTPUT_DIR
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
    """Convertit le Markdown en HTML basique."""
    html = markdown_text

    # Headers
    html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Lists
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html)

    # Numbered lists
    html = re.sub(r'^\d+\.\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Paragraphs (lines not already in tags)
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            result.append(f'<p>{stripped}</p>')
        else:
            result.append(line)
    html = '\n'.join(result)

    # Horizontal rules
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

    return html


def generate_pdf(
    report_markdown: str,
    articles: list[Article],
    editor_report: EditorReport,
    keywords: str,
    date_from: str,
    date_to: str,
    output_path: str | None = None,
) -> str | None:
    """Génère le rapport PDF.

    Returns:
        Chemin du PDF généré, ou None si erreur.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        logger.error("WeasyPrint non installé. PDF non généré.")
        return None
    except OSError as e:
        logger.error(f"WeasyPrint: dépendance système manquante: {e}")
        return None

    try:
        # Prepare template
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("report.html")

        # Convert markdown to HTML
        report_html = _markdown_to_html(report_markdown)

        # Prepare figure data
        figures = editor_report.figures_generated
        figure_captions = []
        for fig_path in figures:
            fname = os.path.basename(fig_path)
            caption = FIGURE_CAPTIONS.get(fname, fname)
            figure_captions.append(caption)

        # Prepare sources string
        sources_list = set(a.source for a in articles)
        sources_str = ", ".join(sorted(sources_list))

        # Prepare verifications
        verifications = [
            {
                "claim": v.claim,
                "verified": v.verified,
                "confidence": v.confidence,
                "correction": v.correction,
            }
            for v in editor_report.verifications
        ]

        # Render HTML
        html_content = template.render(
            title="Rapport de Recherche Bibliographique Scientifique",
            keywords=keywords,
            date_from=date_from,
            date_to=date_to,
            article_count=len(articles),
            sources=sources_str,
            report_date=datetime.now().strftime("%d/%m/%Y %H:%M"),
            confidence_score=editor_report.confidence_score,
            report_html=report_html,
            figures=[os.path.abspath(f) for f in figures],
            figure_captions=figure_captions,
            verifications=verifications,
        )

        # Generate PDF
        if output_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, "rapport_bibliographique.pdf")

        HTML(string=html_content).write_pdf(output_path)
        logger.info(f"PDF généré: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        return None
