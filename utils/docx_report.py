"""Génère un rapport Word (.docx) avec la charte graphique genOway."""

import logging
import os
import re
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import config
from models import Article, EditorReport
from i18n import t

logger = logging.getLogger(__name__)

# ─── Couleurs genOway ────────────────────────────────────────────────────────
GENOWAY_RED = RGBColor(0xE3, 0x06, 0x13)
GENOWAY_DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
GENOWAY_MID_GRAY = RGBColor(0x66, 0x66, 0x66)
GENOWAY_LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
GENOWAY_FONT = "Arial"


# ─── Helpers XML pour la mise en forme ──────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    """Définit la couleur de fond d'une cellule de tableau."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _add_horizontal_rule(doc: Document, color_hex: str = "E30613", thickness_pt: int = 2):
    """Ajoute une ligne horizontale colorée sous le dernier paragraphe."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(thickness_pt * 4))  # 1/8 pt units
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color_hex)
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


# ─── Configuration des styles du document ───────────────────────────────────

def _setup_styles(doc: Document):
    """Configure les styles globaux du document."""
    # Style Normal
    normal = doc.styles["Normal"]
    normal.font.name = GENOWAY_FONT
    normal.font.size = Pt(11)
    normal.font.color.rgb = GENOWAY_DARK_GRAY

    # Style Heading 1 — rouge genOway
    h1 = doc.styles["Heading 1"]
    h1.font.name = GENOWAY_FONT
    h1.font.size = Pt(18)
    h1.font.bold = True
    h1.font.color.rgb = GENOWAY_RED
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(6)

    # Style Heading 2 — gris foncé
    h2 = doc.styles["Heading 2"]
    h2.font.name = GENOWAY_FONT
    h2.font.size = Pt(14)
    h2.font.bold = True
    h2.font.color.rgb = GENOWAY_DARK_GRAY
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)

    # Style Heading 3 — gris moyen
    h3 = doc.styles["Heading 3"]
    h3.font.name = GENOWAY_FONT
    h3.font.size = Pt(12)
    h3.font.bold = True
    h3.font.color.rgb = GENOWAY_MID_GRAY
    h3.paragraph_format.space_before = Pt(8)
    h3.paragraph_format.space_after = Pt(2)


# ─── Page de couverture ──────────────────────────────────────────────────────

def _add_cover_page(doc: Document, title: str, keywords: str,
                    date_from: str, date_to: str, lang: str):
    """Crée la page de couverture avec le branding genOway."""
    # Bandeau rouge en haut via un tableau 1x1
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    cell.width = Cm(21)
    _set_cell_bg(cell, "E30613")
    p = cell.paragraphs[0]
    run = p.add_run("genOway")
    run.font.name = GENOWAY_FONT
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cell._tc.get_or_add_tcPr()
    # Hauteur de cellule
    trPr = table.rows[0]._tr.get_or_add_trPr()
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), "1400")
    trPr.append(trHeight)

    doc.add_paragraph()
    doc.add_paragraph()

    # Titre principal
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(24)
    run_title = p_title.add_run(title)
    run_title.font.name = GENOWAY_FONT
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = GENOWAY_RED

    # Sous-titre : mots-clés
    p_kw = doc.add_paragraph()
    run_kw = p_kw.add_run(keywords)
    run_kw.font.name = GENOWAY_FONT
    run_kw.font.size = Pt(14)
    run_kw.font.color.rgb = GENOWAY_DARK_GRAY

    # Période
    p_period = doc.add_paragraph()
    period_label = "Période : " if lang == "fr" else "Period: "
    run_period = p_period.add_run(f"{period_label}{date_from} — {date_to}")
    run_period.font.name = GENOWAY_FONT
    run_period.font.size = Pt(12)
    run_period.font.color.rgb = GENOWAY_MID_GRAY

    # Date de génération
    p_date = doc.add_paragraph()
    date_label = "Date : " if lang == "fr" else "Date: "
    run_date = p_date.add_run(f"{date_label}{datetime.now().strftime('%d/%m/%Y')}")
    run_date.font.name = GENOWAY_FONT
    run_date.font.size = Pt(12)
    run_date.font.color.rgb = GENOWAY_MID_GRAY

    doc.add_page_break()


# ─── KPI résumé ─────────────────────────────────────────────────────────────

def _add_kpi_section(doc: Document, articles: list[Article],
                     editor_report: EditorReport, lang: str):
    """Ajoute un tableau de KPI visuels."""
    h = doc.add_heading(t("html_articles_analyzed", lang).upper(), level=1)

    sources_list = sorted(set(a.source for a in articles))
    years = [a.year for a in articles if a.year]
    year_range = f"{min(years)}–{max(years)}" if years else "—"

    kpis = [
        (str(len(articles)), t("html_articles_analyzed", lang)),
        (", ".join(sources_list), "Sources"),
        (year_range, t("html_period_covered", lang)),
    ]
    if editor_report.confidence_score > 0:
        kpis.append((f"{editor_report.confidence_score:.0f}%", t("html_factual_confidence", lang)))

    table = doc.add_table(rows=2, cols=len(kpis))
    table.style = "Table Grid"

    for i, (value, label) in enumerate(kpis):
        # Valeur (rouge, grande)
        cell_val = table.rows[0].cells[i]
        _set_cell_bg(cell_val, "F2F2F2")
        p_val = cell_val.paragraphs[0]
        p_val.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_val = p_val.add_run(value)
        run_val.font.name = GENOWAY_FONT
        run_val.font.size = Pt(20)
        run_val.font.bold = True
        run_val.font.color.rgb = GENOWAY_RED

        # Label (gris, petit)
        cell_lbl = table.rows[1].cells[i]
        _set_cell_bg(cell_lbl, "F2F2F2")
        p_lbl = cell_lbl.paragraphs[0]
        p_lbl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_lbl = p_lbl.add_run(label.upper())
        run_lbl.font.name = GENOWAY_FONT
        run_lbl.font.size = Pt(9)
        run_lbl.font.bold = True
        run_lbl.font.color.rgb = GENOWAY_MID_GRAY

    doc.add_paragraph()


# ─── Points clés ────────────────────────────────────────────────────────────

def _add_key_points_section(doc: Document, key_points: list[str], lang: str):
    """Ajoute la section des points clés sous forme de liste à puces."""
    if not key_points:
        return

    title = "Points clés" if lang == "fr" else "Key Points"
    doc.add_heading(title, level=1)
    _add_horizontal_rule(doc)

    for point in key_points:
        p = doc.add_paragraph(style="List Bullet")
        # Recherche du texte entre parenthèses pour le mettre en italique
        parts = re.split(r"(\([^)]+\))", point)
        for i, part in enumerate(parts):
            run = p.add_run(part)
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(11)
            run.font.color.rgb = GENOWAY_DARK_GRAY
            if i % 2 == 1:  # entre parenthèses → source, italique
                run.font.italic = True
                run.font.color.rgb = GENOWAY_MID_GRAY

    doc.add_paragraph()


# ─── Corps du rapport markdown ───────────────────────────────────────────────

def _render_markdown_to_docx(doc: Document, markdown_text: str):
    """Convertit le markdown en paragraphes Word structurés."""
    lines = markdown_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Titres
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
            _add_horizontal_rule(doc)
        # Séparateurs markdown
        elif line.strip() in ("---", "***", "___"):
            _add_horizontal_rule(doc, "CCCCCC", 1)
        # Listes à puces
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            text = line.strip()[2:]
            p = doc.add_paragraph(style="List Bullet")
            _apply_inline_formatting(p, text)
        # Lignes numérotées
        elif re.match(r"^\d+\.\s", line.strip()):
            text = re.sub(r"^\d+\.\s", "", line.strip())
            p = doc.add_paragraph(style="List Number")
            _apply_inline_formatting(p, text)
        # Ligne vide
        elif not line.strip():
            pass
        # Paragraphe normal
        else:
            p = doc.add_paragraph()
            _apply_inline_formatting(p, line)

        i += 1


def _apply_inline_formatting(p, text: str):
    """Applique **gras**, *italique* et [lien](url) sur un paragraphe."""
    # Découpe le texte par patterns inline
    token_pattern = re.compile(
        r"(\*\*[^*]+\*\*|\*[^*]+\*|\[([^\]]+)\]\(([^)]+)\))"
    )
    pos = 0
    for m in token_pattern.finditer(text):
        # Texte avant le match
        if m.start() > pos:
            run = p.add_run(text[pos:m.start()])
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(11)
            run.font.color.rgb = GENOWAY_DARK_GRAY

        matched = m.group(0)
        if matched.startswith("**"):
            # Gras
            run = p.add_run(matched[2:-2])
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = GENOWAY_DARK_GRAY
        elif matched.startswith("*"):
            # Italique
            run = p.add_run(matched[1:-1])
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(11)
            run.font.italic = True
            run.font.color.rgb = GENOWAY_DARK_GRAY
        elif matched.startswith("["):
            # Lien — affiche le texte du lien en bleu souligné
            link_text = m.group(2)
            run = p.add_run(link_text)
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x00, 0x56, 0xB2)
            run.font.underline = True

        pos = m.end()

    # Texte restant après le dernier match
    if pos < len(text):
        run = p.add_run(text[pos:])
        run.font.name = GENOWAY_FONT
        run.font.size = Pt(11)
        run.font.color.rgb = GENOWAY_DARK_GRAY


# ─── Tableau des articles ────────────────────────────────────────────────────

def _add_articles_table(doc: Document, articles: list[Article], lang: str):
    """Ajoute un tableau des articles du corpus."""
    title = t("html_article_corpus", lang)
    doc.add_heading(title, level=1)
    _add_horizontal_rule(doc)

    headers = [
        t("col_title", lang),
        t("col_authors", lang),
        t("col_journal", lang),
        t("col_year", lang),
        t("col_citations", lang),
        "DOI",
    ]

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"

    # En-tête
    hdr_row = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        _set_cell_bg(cell, "E30613")
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.font.name = GENOWAY_FONT
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Données
    for a in articles[:100]:  # Cap à 100 pour éviter les fichiers gigantesques
        row = table.add_row()
        values = [
            a.title[:80] + ("…" if len(a.title) > 80 else ""),
            ", ".join(a.authors[:3]) + ("…" if len(a.authors) > 3 else ""),
            a.journal or "—",
            str(a.year) if a.year else "—",
            str(a.citation_count),
            a.doi or "—",
        ]
        for i, val in enumerate(values):
            cell = row.cells[i]
            p = cell.paragraphs[0]
            run = p.add_run(val)
            run.font.name = GENOWAY_FONT
            run.font.size = Pt(8)
            run.font.color.rgb = GENOWAY_DARK_GRAY

    doc.add_paragraph()


# ─── Pied de page ───────────────────────────────────────────────────────────

def _add_footer(doc: Document, lang: str):
    """Ajoute un pied de page genOway sur toutes les sections."""
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.clear()
    run_brand = p.add_run("genOway")
    run_brand.font.name = GENOWAY_FONT
    run_brand.font.size = Pt(9)
    run_brand.font.bold = True
    run_brand.font.color.rgb = GENOWAY_RED
    run_sep = p.add_run("  |  www.genoway.com  |  Confidentiel" if lang == "fr"
                        else "  |  www.genoway.com  |  Confidential")
    run_sep.font.name = GENOWAY_FONT
    run_sep.font.size = Pt(9)
    run_sep.font.color.rgb = GENOWAY_MID_GRAY
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ─── Fonction principale ─────────────────────────────────────────────────────

def generate_docx(
    report_markdown: str,
    articles: list[Article],
    editor_report: EditorReport,
    keywords: str,
    date_from: str,
    date_to: str,
    key_points: list[str] | None = None,
    lang: str = "fr",
) -> str:
    """Génère un rapport Word avec la charte graphique genOway.

    Returns:
        Chemin vers le fichier .docx généré
    """
    doc = Document()

    # Marges de page
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    _setup_styles(doc)
    _add_footer(doc, lang)

    # 1. Page de couverture
    _add_cover_page(doc, t("html_title", lang), keywords, date_from, date_to, lang)

    # 2. KPIs
    _add_kpi_section(doc, articles, editor_report, lang)
    doc.add_page_break()

    # 3. Points clés
    if key_points:
        _add_key_points_section(doc, key_points, lang)
        doc.add_page_break()

    # 4. Corps du rapport
    report_title = t("html_synthesis_report", lang)
    doc.add_heading(report_title, level=1)
    _add_horizontal_rule(doc)
    _render_markdown_to_docx(doc, report_markdown)
    doc.add_page_break()

    # 5. Tableau des articles
    _add_articles_table(doc, articles, lang)

    # Sauvegarde
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(config.OUTPUT_DIR, "rapport_bibliographique.docx")
    doc.save(output_path)

    logger.info(f"DOCX report generated: {output_path}")
    return output_path
