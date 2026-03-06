"""Generation of downloadable HTML infographic report."""

import base64
import logging
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
import markdown as md

import config
from models import Article, EditorReport
from i18n import t

logger = logging.getLogger(__name__)


def _markdown_to_html(markdown_text: str) -> str:
    return md.markdown(
        markdown_text,
        extensions=["extra", "smarty", "sane_lists", "toc"],
        output_format="html",
    )


def _encode_figure_b64(fig_path: str) -> str | None:
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
    lang: str = "fr",
) -> str:
    """Generate standalone HTML infographic report.

    Returns:
        Complete HTML content (string) ready for download.
    """
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("report.html")

    report_html = _markdown_to_html(report_markdown)

    # Figures as base64
    figure_caption_map = {
        "timeline.png": t("fig_timeline", lang),
        "top_journals.png": t("fig_top_journals", lang),
        "wordcloud.png": t("fig_wordcloud", lang),
        "cocitation_network.png": t("fig_cocitation", lang),
        "theme_heatmap.png": t("fig_heatmap", lang),
    }

    figures_b64 = []
    for fig_path in editor_report.figures_generated:
        b64 = _encode_figure_b64(fig_path)
        if b64:
            fname = os.path.basename(fig_path)
            caption = figure_caption_map.get(fname, fname)
            figures_b64.append({"data": b64, "caption": caption})

    sources_list = set(a.source for a in articles)
    sources_str = ", ".join(sorted(sources_list))

    years = [a.year for a in articles if a.year]
    year_range = f"{min(years)}-{max(years)}" if years else ""

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

    # Translated labels for the template
    labels = {
        "articles_analyzed": t("html_articles_analyzed", lang),
        "sources": "Sources",
        "factual_confidence": t("html_factual_confidence", lang),
        "period_covered": t("html_period_covered", lang),
        "synthesis_report": t("html_synthesis_report", lang),
        "infographics": t("html_infographics", lang),
        "article_corpus": t("html_article_corpus", lang),
        "factual_verification": t("html_factual_verification", lang),
        "footer": t("html_footer", lang),
        "col_title": t("col_title", lang),
        "col_authors": t("col_authors", lang),
        "col_journal": t("col_journal", lang),
        "col_year": t("col_year", lang),
        "col_citations": t("col_citations", lang),
        "status_corrected": t("status_corrected", lang),
        "status_verified": t("status_verified", lang),
        "status_unverified": t("status_unverified", lang),
        "label_confidence": t("label_confidence", lang),
        "label_source": t("label_source", lang),
        "label_correction": t("label_correction", lang),
    }

    html_content = template.render(
        title=t("html_title", lang),
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
        labels=labels,
        lang=lang,
    )

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
